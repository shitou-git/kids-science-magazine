import json
import os
import re
import shutil
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

import config
from crawler import collect_news
from ai_processor import classify_article, rewrite_for_kids, select_headline
from image_fetcher import get_article_image


def fallback_classify(article, categories):
    title = article["title"].lower()
    content = article["content"][:1000].lower()
    text = title + " " + content

    best_cat = None
    best_score = 0

    for cat in categories:
        score = 0
        for keyword in cat["keywords"]:
            if keyword.lower() in text:
                score += 1
        if score > best_score:
            best_score = score
            best_cat = cat["id"]

    # 头条类只在分数很高时才归入
    if best_cat == "headline" and best_score < 2:
        return None

    return best_cat


def fallback_select_headline(articles):
    if not articles:
        return None
    # 优先选少儿友好分最高的文章
    return max(articles, key=lambda a: a.get("kid_score", 0))


def get_issue_number():
    archive_dir = config.ARCHIVE_DIR
    if not os.path.exists(archive_dir):
        return 1
    issues = [f for f in os.listdir(archive_dir) if f.startswith("issue_")]
    if not issues:
        return 1
    numbers = []
    for f in issues:
        m = re.search(r"issue_(\d+)", f)
        if m:
            numbers.append(int(m.group(1)))
    return max(numbers) + 1 if numbers else 1


def text_to_html_paragraphs(text):
    if not text:
        return ""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    html_parts = []
    for p in paragraphs:
        html_parts.append(f"<p>{p}</p>")
    return "\n".join(html_parts)


def process_articles(raw_articles):
    print("\n" + "="*60)
    print("开始AI内容处理...")
    print("="*60)

    categories = {cat["id"]: {**cat, "articles": []} for cat in config.CATEGORIES}

    print(f"\n共 {len(raw_articles)} 篇文章待分类...")
    for i, article in enumerate(raw_articles):
        print(f"\n[{i+1}/{len(raw_articles)}] 分类中: {article['title'][:40]}...")
        cat_id = classify_article(article, config.CATEGORIES)
        if not cat_id:
            cat_id = fallback_classify(article, config.CATEGORIES)
        if cat_id and cat_id in categories:
            categories[cat_id]["articles"].append(article)
            print(f"  → 归类到: {categories[cat_id]['name']}")
        else:
            print(f"  → 无法分类，跳过")

    result_categories = []

    # 第一步：先选头版头条
    headline_article = None
    headline_cat_id = None
    all_articles = []
    for c in categories.values():
        all_articles.extend(c["articles"])

    print(f"\n🌟 选择头版头条...")
    selected = select_headline(all_articles)
    if not selected:
        selected = fallback_select_headline(all_articles)
    if selected:
        print(f"  头条: {selected['title'][:40]}...")
        headline_article = selected
        # 找出头条属于哪个栏目
        for cat_id, cat_data in categories.items():
            if selected in cat_data["articles"]:
                headline_cat_id = cat_id
                break

    # 第二步：为每个栏目选文章，跳过头条文章
    for cat in config.CATEGORIES:
        cat_data = categories[cat["id"]]
        selected_article = None

        if cat["id"] == "headline":
            if headline_article:
                selected_article = process_single_article(headline_article, cat["id"], 0)
        else:
            articles = cat_data["articles"]
            # 过滤掉头条文章，避免重复
            if headline_article:
                articles = [a for a in articles if a["hash"] != headline_article["hash"]]
            if articles:
                print(f"\n📝 {cat['name']}: 改写 {len(articles)} 篇，选最优...")
                best_article = None
                for idx, art in enumerate(articles[:config.ARTICLES_PER_CATEGORY + 2]):
                    processed = process_single_article(art, cat["id"], idx)
                    if processed:
                        best_article = processed
                        break
                selected_article = best_article

        cat_data["article"] = selected_article
        result_categories.append(cat_data)

    return result_categories


def fallback_process(article):
    content = article["content"]
    paragraphs = [p.strip() for p in content.split("\n") if p.strip() and len(p.strip()) > 20]
    if paragraphs:
        selected = []
        current_len = 0
        for p in paragraphs:
            if current_len < 400:
                selected.append(p)
                current_len += len(p)
            else:
                break
        kid_content = "\n".join(selected)
    else:
        kid_content = content[:400]

    highlight = paragraphs[0][:30] + "..." if paragraphs else ""

    golden_sentences = [
        "好奇心是最好的老师",
        "探索永无止境",
        "科学改变世界",
        "知识就是力量",
        "每一个发现都从提问开始",
        "用心观察，处处是科学",
        "坚持探索，终有收获",
        "大自然充满奥秘",
    ]
    import random
    golden_sentence = random.choice(golden_sentences)

    personality_points = [
        "好奇心",
        "探索精神",
        "勇于发现",
        "科学思维",
        "坚持不懈",
        "善于观察",
    ]
    personality_point = random.choice(personality_points)

    return {
        "title": article["title"],
        "content": kid_content,
        "highlight": highlight,
        "golden_sentence": golden_sentence,
        "personality_point": personality_point,
    }


def process_single_article(article, category_id, index):
    issue_id = "current"
    print(f"  AI改写中...")

    rewritten = rewrite_for_kids(article)
    if not rewritten:
        print(f"    ⚠️  AI不可用，使用原文简化处理")
        rewritten = fallback_process(article)

    print(f"    ✓ 标题: {rewritten['title'][:30]}...")

    article["kid_title"] = rewritten["title"]
    article["kid_content"] = rewritten["content"]
    article["highlight"] = rewritten.get("highlight", "")
    article["content_html"] = text_to_html_paragraphs(rewritten["content"])

    print(f"  🖼️  获取配图...")
    image = get_article_image(article, category_id, issue_id)
    article["image"] = image

    return {
        "title": rewritten["title"],
        "content": rewritten["content"],
        "content_html": article["content_html"],
        "highlight": rewritten.get("highlight", ""),
        "golden_sentence": rewritten.get("golden_sentence", ""),
        "personality_point": rewritten.get("personality_point", ""),
        "image": image,
        "source": article.get("source", ""),
        "url": article.get("url", ""),
    }


def generate_html(categories, issue_number, publish_date):
    print("\n" + "="*60)
    print("生成HTML杂志...")
    print("="*60)

    headline_cat = None
    other_categories = []
    for cat in categories:
        if cat["id"] == "headline":
            headline_cat = cat
        else:
            other_categories.append(cat)

    headline_article = headline_cat["article"] if headline_cat else None

    env = Environment(loader=FileSystemLoader(config.TEMPLATES_DIR))
    template = env.get_template("magazine.html")

    html = template.render(
        magazine_title="少年科普周刊",
        issue_number=issue_number,
        publish_date=publish_date,
        categories=other_categories,
        headline_article=headline_article,
    )

    return html


def save_issue(html_content, issue_number):
    issue_dir = os.path.join(config.ARCHIVE_DIR, f"issue_{issue_number}")
    os.makedirs(issue_dir, exist_ok=True)

    html_path = os.path.join(issue_dir, f"issue_{issue_number}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    images_src = os.path.join(config.IMAGES_DIR)
    images_dst = os.path.join(issue_dir, "images")
    if os.path.exists(images_src) and os.listdir(images_src):
        if os.path.exists(images_dst):
            shutil.rmtree(images_dst)
        shutil.copytree(images_src, images_dst)

    latest_path = os.path.join(config.OUTPUT_DIR, "latest.html")
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(html_content.replace('src="images/', f'src="archive/issue_{issue_number}/images/'))

    print(f"\n✅ 周刊已保存:")
    print(f"   归档: {html_path}")
    print(f"   最新: {latest_path}")

    return html_path


def create_homepage():
    """创建主页 index.html，列出所有期数"""
    issues = []
    if os.path.exists(config.ARCHIVE_DIR):
        for name in sorted(os.listdir(config.ARCHIVE_DIR), reverse=True):
            if name.startswith("issue_"):
                num = name.replace("issue_", "")
                issues.append({
                    "number": num,
                    "path": f"./{name}/issue_{num}.html",
                    "is_latest": len(issues) == 0
                })

    if not issues:
        return

    latest = issues[0]
    issue_links = ""
    for issue in issues:
        badge = '<span class="badge">最新</span>' if issue["is_latest"] else ""
        issue_links += f'                <a href="{issue["path"]}" class="issue-link">\n                    第 {issue["number"]} 期 {badge}\n                </a>\n'

    homepage_html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>少年科普周刊</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif;
            background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: #333;
        }}
        .container {{
            text-align: center;
            padding: 40px;
            max-width: 600px;
        }}
        .logo {{ font-size: 80px; margin-bottom: 20px; }}
        h1 {{
            font-size: 36px;
            font-weight: 900;
            color: #fff;
            text-shadow: 2px 4px 8px rgba(0,0,0,0.15);
            margin-bottom: 12px;
            letter-spacing: 4px;
        }}
        .subtitle {{
            font-size: 16px;
            color: rgba(255,255,255,0.9);
            letter-spacing: 8px;
            margin-bottom: 40px;
        }}
        .card {{
            background: rgba(255,255,255,0.95);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 12px 40px rgba(0,0,0,0.1);
        }}
        .btn {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 14px 36px;
            border-radius: 50px;
            text-decoration: none;
            font-weight: 700;
            font-size: 16px;
            transition: transform 0.3s;
            box-shadow: 0 4px 16px rgba(102,126,234,0.4);
        }}
        .btn:hover {{ transform: translateY(-2px); }}
        .issues-list {{ margin-top: 30px; text-align: left; }}
        .issues-list h3 {{
            font-size: 14px;
            color: #888;
            margin-bottom: 12px;
            text-align: center;
        }}
        .issue-link {{
            display: block;
            padding: 12px 16px;
            background: #f8f9fa;
            border-radius: 12px;
            margin-bottom: 8px;
            text-decoration: none;
            color: #333;
            font-weight: 600;
            transition: all 0.3s;
        }}
        .issue-link:hover {{
            background: #eef2ff;
            transform: translateX(4px);
        }}
        .issue-link .badge {{
            display: inline-block;
            background: linear-gradient(135deg, #ff6b9d, #feca57);
            color: #fff;
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 12px;
            margin-left: 8px;
        }}
        .footer {{
            margin-top: 30px;
            font-size: 13px;
            color: rgba(255,255,255,0.7);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">🔬</div>
        <h1>少年科普周刊</h1>
        <p class="subtitle">少 年 科 普 周 刊</p>

        <div class="card">
            <a href="{latest["path"]}" class="btn">📖 阅读最新一期</a>
        </div>

        <div class="card">
            <div class="issues-list">
                <h3>📋 往期回顾</h3>
{issue_links}
            </div>
        </div>

        <div class="footer">
            <p>每周五晚8点更新 · 带你探索科学的奇妙世界</p>
            <p style="margin-top:8px;">保持好奇，热爱探索 🔬</p>
        </div>
    </div>
</body>
</html>'''

    index_path = os.path.join(config.ARCHIVE_DIR, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(homepage_html)
    print(f"   主页: {index_path}")


def run_weekly_task():
    print("\n" + "="*60)
    print("🚀 少年科普周刊 - 开始生成")
    print("="*60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    os.makedirs(config.IMAGES_DIR, exist_ok=True)
    os.makedirs(config.ARCHIVE_DIR, exist_ok=True)

    for f in os.listdir(config.IMAGES_DIR):
        os.remove(os.path.join(config.IMAGES_DIR, f))

    issue_number = get_issue_number()
    publish_date = datetime.now().strftime("%Y年%m月%d日")

    print(f"\n第 {issue_number} 期 · {publish_date}")

    raw_articles = collect_news()
    if not raw_articles:
        print("❌ 未采集到任何文章！")
        return None

    categories = process_articles(raw_articles)

    html_content = generate_html(categories, issue_number, publish_date)

    save_issue(html_content, issue_number)
    create_homepage()

    print("\n" + "="*60)
    print(f"🎉 第 {issue_number} 期周刊生成完成！")
    print("="*60)

    return issue_number


def main():
    import schedule
    import time

    print("\n🌟 少年科普周刊 - 自动生成系统 🌟")
    print("="*60)
    print(f"发布时间: 每周五 20:00")
    print(f"AI API: {config.AI_API_BASE_URL}")
    print(f"API密钥已配置: {'是' if config.AI_API_KEY else '否'}")
    print("="*60)

    if not config.AI_API_KEY:
        print("\n⚠️  警告: 未配置 AGENS_AI_API_KEY 环境变量")
        print("请设置环境变量: export AGENS_AI_API_KEY='你的API密钥'")

    schedule.every().friday.at("20:00").do(run_weekly_task)

    print("\n📅 已设置每周五20:00自动生成周刊")
    print("💡 输入 'run' 立即生成一期测试")
    print("💡 输入 'quit' 退出程序")

    import threading

    def run_schedule():
        while True:
            schedule.run_pending()
            time.sleep(60)

    schedule_thread = threading.Thread(target=run_schedule, daemon=True)
    schedule_thread.start()

    try:
        while True:
            cmd = input("\n> ").strip().lower()
            if cmd == "run":
                run_weekly_task()
            elif cmd == "quit" or cmd == "exit":
                print("👋 再见！")
                break
            else:
                print("未知命令。可用命令: run, quit")
    except KeyboardInterrupt:
        print("\n👋 程序已终止")


if __name__ == "__main__":
    main()
