import json

import requests

import config


def call_ai_api(messages, temperature=0.7, max_tokens=1000):
    if not config.AI_API_KEY:
        print("警告: 未配置AI API密钥")
        return None

    url = f"{config.AI_API_BASE_URL}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.AI_API_KEY}",
    }
    data = {
        "model": config.AI_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"AI API调用失败: {e}")
        return None


def classify_article(article, categories):
    title = article["title"]
    content = article["content"][:500]

    category_list = "\n".join([f"- {cat['id']}: {cat['name']}（关键词：{', '.join(cat['keywords'][:5])}）" for cat in categories])

    system_prompt = "你是一位专业的少儿科普编辑，擅长将科普文章分类，同时判断内容是否适合小学生阅读。"
    user_prompt = f"""请将以下科普文章归类到最合适的栏目中，并判断其是否适合小学生（8-12岁）阅读。

栏目列表：
{category_list}

文章标题：{title}
文章摘要：{content}

判断标准：
- 适合：科学知识浅显易懂、主题积极有趣、小朋友会感兴趣
- 不适合：内容过于学术、涉及政治/负面话题、太枯燥

请以JSON格式返回：
{{"category": "栏目ID", "kid_friendly": true/false}}

只返回JSON，不要其他文字。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    result = call_ai_api(messages, temperature=0.3, max_tokens=100)
    if result:
        try:
            result = result.strip()
            if result.startswith("```json"):
                result = result[7:]
            if result.startswith("```"):
                result = result[3:]
            if result.endswith("```"):
                result = result[:-3]
            result = result.strip()
            parsed = json.loads(result)
            cat_id = parsed.get("category", "")
            kid_friendly = parsed.get("kid_friendly", True)
            if not kid_friendly:
                return None  # 不适合少儿，跳过
            for cat in categories:
                if cat["id"] in cat_id:
                    return cat["id"]
        except Exception:
            # JSON解析失败，退回旧逻辑
            result = result.strip()
            for cat in categories:
                if cat["id"] in result:
                    return cat["id"]
    return None


def rewrite_for_kids(article, target_length=350):
    title = article["title"]
    content = article["content"][:2000]

    system_prompt = """你是一位资深的少儿科普编辑，专门为小学3-6年级学生（8-12岁）编写科普读物。

你的写作风格参考"阳光少年报"：
1. 用讲故事的方式开头，比如"你有没有想过..."、"你知道吗..."
2. 语言像跟好朋友聊天一样自然亲切
3. 把复杂的科学知识变成小朋友能理解的生活场景
4. 多用比喻和拟人，比如"白细胞就像身体里的警察"
5. 每段不超过3-4句话，短句为主
6. 加入互动感：反问、惊叹、"你猜怎么着？"
7. 用emoji增加趣味性（每段最多1个）
8. 绝对不用：学术术语、复杂公式、政治话题、负面内容
9. 字数控制在250-350字
10. 三段式结构：引人入胜的开头 → 有趣的知识讲解 → 启发式结尾"""

    user_prompt = f"""请将下面这篇科普文章改写成小学生爱看的版本。

要求：
- 目标读者：8-12岁小学生
- 读起来像故事，不像教科书
- 小朋友看完会觉得"哇，好有趣！"
- 适合朗读，句子要短

原文标题：{title}
原文内容：
{content}

请以JSON格式返回，包含以下字段：
- title: 吸引小朋友的新标题（10-15字，有趣、有悬念、像问句更好）
- content: 改写后的正文（250-350字，分3-4段，每段3-4句话，生动有趣）
- highlight: 一句话核心知识点（15-20字，用小朋友能懂的话说）
- golden_sentence: 金句素材（一句话正能量总结，可以用在作文里，20字以内）
- personality_point: 人格点亮（这篇文章教会我们什么品质？比如：好奇心、坚持、探索精神等，4-6个字）

只返回JSON，不要其他文字。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    result = call_ai_api(messages, temperature=0.8, max_tokens=800)
    if result:
        try:
            result = result.strip()
            if result.startswith("```json"):
                result = result[7:]
            if result.startswith("```"):
                result = result[3:]
            if result.endswith("```"):
                result = result[:-3]
            result = result.strip()
            parsed = json.loads(result)
            return parsed
        except Exception as e:
            print(f"AI返回解析失败: {e}")
            print(f"原始返回: {result[:200]}")
    return None


def select_headline(articles):
    if not articles:
        return None

    summaries = []
    for i, art in enumerate(articles[:10]):
        summaries.append(f"{i+1}. 标题：{art['title']}\n   摘要：{art['content'][:100]}...")

    system_prompt = "你是一位资深的少儿报纸主编，擅长挑选最有价值的头版头条新闻。"
    user_prompt = f"""以下是本周的科普新闻列表，请选出最适合作为头版头条的一篇。

评选标准：
1. 新闻价值高，是本周重大科学事件
2. 小朋友会感兴趣，有吸引力
3. 积极正面，能激发科学热情

新闻列表：
{chr(10).join(summaries)}

请只返回你选中的新闻编号（1-10），不要返回其他任何文字。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    result = call_ai_api(messages, temperature=0.5, max_tokens=20)
    if result:
        result = result.strip()
        for i in range(len(articles[:10]), 0, -1):
            if str(i) in result:
                return articles[i - 1]
    return articles[0] if articles else None


def generate_image_prompt(article):
    title = article.get("title", "")
    highlight = article.get("highlight", "")
    content = article.get("kid_content", article.get("content", ""))[:300]

    system_prompt = "你是一位专业的插画师，擅长为少儿科普文章设计配图。"
    user_prompt = f"""请为以下少儿科普文章生成一张配图的描述（用于AI绘图）。

文章标题：{title}
核心知识点：{highlight}
文章内容：{content}

要求：
1. 风格：卡通、可爱、色彩明亮、适合儿童
2. 主体突出，画面有趣
3. 用英文描述，50个单词以内
4. 适合作为文章插图

只返回英文的图片描述，不要其他文字。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    result = call_ai_api(messages, temperature=0.7, max_tokens=100)
    return result.strip() if result else ""
