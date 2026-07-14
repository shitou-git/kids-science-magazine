import json
import os
import re
import shutil
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

import config
from crawler import collect_news
from ai_processor import classify_article, rewrite_for_kids, select_headline
from image_fetcher import get_article_images


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
        if cat_id and cat_id in categories and cat_id != "headline":
            categories[cat_id]["articles"].append(article)
            print(f"  → 归类到: {categories[cat_id]['name']}")
        elif cat_id == "headline":
            categories["headline"]["articles"].append(article)
            print(f"  → 归类到: 头条候选")
        else:
            print(f"  → 无法分类，跳过")

    result_categories = []

    # 第一步：先选头版头条
    headline_article = None
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

    # 添加头条栏目
    headline_cat = {
        "id": "headline",
        "name": "今日头条",
        "icon": "🌟",
        "article": process_single_article(headline_article, "headline", 0) if headline_article else None
    }
    result_categories.append(headline_cat)

    selected_hashes = set()
    if headline_article:
        selected_hashes.add(headline_article["hash"])

    # 筛选有文章的栏目，排除头条
    available_cats = []
    for cat_id, cat_data in categories.items():
        if cat_id != "headline":
            articles = [a for a in cat_data["articles"] if a["hash"] not in selected_hashes]
            if articles:
                available_cats.append({
                    "id": cat_id,
                    "name": cat_data["name"],
                    "icon": cat_data["icon"],
                    "articles": articles
                })

    # 按文章数量排序，选前几个栏目
    available_cats.sort(key=lambda x: len(x["articles"]), reverse=True)
    selected_cats = available_cats[:config.DAILY_TOPICS_COUNT - 1]

    print(f"\n📋 今日选择 {len(selected_cats) + 1} 个主题（头条 + {len(selected_cats)}个栏目）")

    for cat_info in selected_cats:
        print(f"\n📝 {cat_info['name']}: 改写 {len(cat_info['articles'])} 篇，选最优...")

        best_article = None
        for idx, art in enumerate(cat_info["articles"][:config.ARTICLES_PER_CATEGORY + 2]):
            processed = process_single_article(art, cat_info["id"], idx)
            if processed:
                best_article = processed
                break

        cat_data = {
            "id": cat_info["id"],
            "name": cat_info["name"],
            "icon": cat_info["icon"],
            "article": best_article
        }
        result_categories.append(cat_data)

    return result_categories


def fallback_process(article):
    content = article["content"]
    paragraphs = [p.strip() for p in content.split("\n") if p.strip() and len(p.strip()) > 20]
    if paragraphs:
        selected = []
        current_len = 0
        for p in paragraphs:
            if current_len < config.MIN_CONTENT_LENGTH:
                selected.append(p)
                current_len += len(p)
            else:
                break
        kid_content = "\n".join(selected)
    else:
        kid_content = content[:config.MIN_CONTENT_LENGTH]

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
    images = get_article_images(article, category_id, issue_id, max_images=3)
    article["images"] = images

    return {
        "title": rewritten["title"],
        "content": rewritten["content"],
        "content_html": article["content_html"],
        "highlight": rewritten.get("highlight", ""),
        "golden_sentence": rewritten.get("golden_sentence", ""),
        "personality_point": rewritten.get("personality_point", ""),
        "image": images[0] if images else None,
        "images": images,
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
    <title>少年科普周刊 - 阳光少年报风格</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(180deg, #FFF5E6 0%, #FFF0D4 100%);
            min-height: 100vh;
            color: #333;
        }}
        .header {{
            background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%);
            padding: 60px 20px 40px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}
        .header::before {{
            content: '★';
            position: absolute;
            top: 20px;
            left: 30px;
            font-size: 48px;
            color: rgba(255,255,255,0.3);
            animation: spin 10s linear infinite;
        }}
        .header::after {{
            content: '☆';
            position: absolute;
            bottom: 20px;
            right: 30px;
            font-size: 36px;
            color: rgba(255,255,255,0.3);
            animation: spin 12s linear infinite reverse;
        }}
        @keyframes spin {{
            from {{ transform: rotate(0deg); }}
            to {{ transform: rotate(360deg); }}
        }}
        .logo-box {{
            display: inline-block;
            background: rgba(255,255,255,0.95);
            padding: 12px 24px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.15);
        }}
        .logo-text {{
            font-size: 20px;
            font-weight: 800;
            color: #FF6B35;
            letter-spacing: 4px;
        }}
        h1 {{
            font-size: 48px;
            font-weight: 900;
            color: #fff;
            margin-bottom: 12px;
            letter-spacing: 8px;
            text-shadow: 2px 4px 8px rgba(0,0,0,0.2);
        }}
        .subtitle {{
            font-size: 16px;
            color: rgba(255,255,255,0.9);
            letter-spacing: 10px;
            font-weight: 500;
        }}
        .feature-box {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 30px;
            flex-wrap: wrap;
        }}
        .feature-item {{
            background: rgba(255,255,255,0.95);
            padding: 16px 24px;
            border-radius: 50px;
            font-size: 14px;
            font-weight: 600;
            color: #FF6B35;
            box-shadow: 0 4px 16px rgba(255,107,53,0.2);
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .main-content {{
            max-width: 900px;
            margin: -30px auto 0;
            padding: 0 20px;
            position: relative;
            z-index: 1;
        }}
        .hero-card {{
            background: #fff;
            border-radius: 24px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 12px 48px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .hero-image {{
            width: 100%;
            height: 280px;
            border-radius: 16px;
            object-fit: cover;
            margin-bottom: 24px;
            box-shadow: 0 8px 28px rgba(0,0,0,0.1);
        }}
        .hero-title {{
            font-size: 28px;
            font-weight: 800;
            color: #1a1a2e;
            margin-bottom: 12px;
            line-height: 1.5;
        }}
        .hero-desc {{
            font-size: 15px;
            color: #666;
            margin-bottom: 24px;
            line-height: 1.8;
        }}
        .btn-primary {{
            display: inline-block;
            background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%);
            color: #fff;
            padding: 16px 48px;
            border-radius: 50px;
            text-decoration: none;
            font-weight: 700;
            font-size: 18px;
            transition: all 0.3s;
            box-shadow: 0 6px 24px rgba(255,107,53,0.35);
        }}
        .btn-primary:hover {{
            transform: translateY(-3px);
            box-shadow: 0 10px 36px rgba(255,107,53,0.45);
        }}
        .sections-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 24px;
            margin-bottom: 30px;
        }}
        .section-card {{
            background: #fff;
            border-radius: 20px;
            padding: 28px;
            box-shadow: 0 8px 28px rgba(0,0,0,0.08);
            transition: all 0.3s;
            border-top: 4px solid transparent;
        }}
        .section-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 12px 36px rgba(0,0,0,0.12);
        }}
        .section-card:nth-child(1) {{ border-top-color: #FF6B35; }}
        .section-card:nth-child(2) {{ border-top-color: #4ECDC4; }}
        .section-card:nth-child(3) {{ border-top-color: #45B7D1; }}
        .section-card:nth-child(4) {{ border-top-color: #96CEB4; }}
        .section-card:nth-child(5) {{ border-top-color: #FFEAA7; }}
        .section-card:nth-child(6) {{ border-top-color: #DDA0DD; }}
        .section-card:nth-child(7) {{ border-top-color: #98D8C8; }}
        .section-card:nth-child(8) {{ border-top-color: #F7DC6F; }}
        .section-icon {{
            font-size: 40px;
            margin-bottom: 12px;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: 700;
            color: #1a1a2e;
            margin-bottom: 8px;
        }}
        .section-desc {{
            font-size: 13px;
            color: #888;
            line-height: 1.6;
        }}
        .issues-section {{
            background: #fff;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 8px 28px rgba(0,0,0,0.08);
        }}
        .section-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 2px solid #f0f0f0;
        }}
        .section-header h2 {{
            font-size: 20px;
            font-weight: 800;
            color: #1a1a2e;
        }}
        .issues-list {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}
        .issue-link {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 20px;
            background: #f8f9fa;
            border-radius: 12px;
            text-decoration: none;
            color: #333;
            transition: all 0.3s;
        }}
        .issue-link:hover {{
            background: #fff5e6;
            transform: translateX(4px);
            box-shadow: 0 4px 12px rgba(255,107,53,0.1);
        }}
        .issue-info {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .issue-number {{
            font-size: 28px;
            font-weight: 900;
            color: #FF6B35;
        }}
        .issue-text {{
            font-weight: 600;
            font-size: 15px;
        }}
        .issue-date {{
            font-size: 13px;
            color: #999;
        }}
        .issue-badge {{
            background: linear-gradient(135deg, #FF6B35, #F7931E);
            color: #fff;
            padding: 6px 16px;
            border-radius: 50px;
            font-size: 12px;
            font-weight: 600;
        }}
        .footer {{
            background: #2d3436;
            color: rgba(255,255,255,0.7);
            padding: 40px 20px;
            text-align: center;
            margin-top: 50px;
        }}
        .footer-title {{
            font-size: 20px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 10px;
        }}
        .footer-text {{
            font-size: 14px;
            margin-bottom: 6px;
        }}
        .footer-slogan {{
            font-size: 13px;
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid rgba(255,255,255,0.1);
            opacity: 0.7;
        }}
        @media (max-width: 768px) {{
            h1 {{ font-size: 32px; letter-spacing: 4px; }}
            .subtitle {{ font-size: 13px; letter-spacing: 6px; }}
            .feature-box {{ gap: 12px; }}
            .feature-item {{ padding: 10px 16px; font-size: 12px; }}
            .hero-card {{ padding: 24px; }}
            .hero-title {{ font-size: 22px; }}
            .hero-image {{ height: 200px; }}
            .btn-primary {{ padding: 14px 32px; font-size: 16px; }}
            .sections-grid {{ grid-template-columns: 1fr; }}
            .section-card {{ padding: 20px; }}
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="logo-box">
            <span class="logo-text">☀️ 阳光少年报风格</span>
        </div>
        <h1>少年科普周刊</h1>
        <p class="subtitle">少 年 科 普 周 刊</p>
        <div class="feature-box">
            <div class="feature-item">📚 每周五发布</div>
            <div class="feature-item">🔬 前沿科普</div>
            <div class="feature-item">🌟 榜样力量</div>
            <div class="feature-item">✨ 人格点亮</div>
        </div>
    </header>

    <main class="main-content">
        <div class="hero-card">
            <img src="https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&q=80" alt="科学探索" class="hero-image">
            <h2 class="hero-title">开启奇妙的科学之旅</h2>
            <p class="hero-desc">专为小学生打造的科普周刊，带你探索宇宙奥秘、发现自然神奇、了解前沿科技。让每个孩子都成为小小科学家！</p>
            <a href="{latest["path"]}" class="btn-primary">📖 阅读最新一期</a>
        </div>

        <div class="sections-grid">
            <div class="section-card">
                <div class="section-icon">🌟</div>
                <h3 class="section-title">榜样力量</h3>
                <p class="section-desc">认识时代先锋、平凡英雄，学习他们的优秀品质</p>
            </div>
            <div class="section-card">
                <div class="section-icon">🇨🇳</div>
                <h3 class="section-title">中国故事</h3>
                <p class="section-desc">了解祖国发展成就，增强文化自信</p>
            </div>
            <div class="section-card">
                <div class="section-icon">🌍</div>
                <h3 class="section-title">多元世界</h3>
                <p class="section-desc">探索全球动态，培养国际视野</p>
            </div>
            <div class="section-card">
                <div class="section-icon">💡</div>
                <h3 class="section-title">科学创新</h3>
                <p class="section-desc">追踪前沿科技，激发探索热情</p>
            </div>
            <div class="section-card">
                <div class="section-icon">🔮</div>
                <h3 class="section-title">趣味自然</h3>
                <p class="section-desc">发现奇趣知识，满足好奇心</p>
            </div>
            <div class="section-card">
                <div class="section-icon">🎨</div>
                <h3 class="section-title">文化之旅</h3>
                <p class="section-desc">感受历史文化，传承文明智慧</p>
            </div>
            <div class="section-card">
                <div class="section-icon">🗺️</div>
                <h3 class="section-title">身边故事</h3>
                <p class="section-desc">关注身边小事，发现温暖瞬间</p>
            </div>
            <div class="section-card">
                <div class="section-icon">🎭</div>
                <h3 class="section-title">漫画乐园</h3>
                <p class="section-desc">轻松幽默漫画，快乐学习知识</p>
            </div>
        </div>

        <div class="issues-section">
            <div class="section-header">
                <span>📋</span>
                <h2>往期回顾</h2>
            </div>
            <div class="issues-list">
{issue_links}
            </div>
        </div>
    </main>

    <footer class="footer">
        <p class="footer-title">少年科普周刊</p>
        <p class="footer-text">每天下午4点，带你探索科学的奇妙世界</p>
        <p class="footer-text">专为小学生打造的科普读物</p>
        <p class="footer-slogan">保持好奇，热爱探索，每个孩子都是小小科学家 🔬</p>
    </footer>
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
        create_homepage()
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
