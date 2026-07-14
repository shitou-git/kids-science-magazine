import base64
import os
import re
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

import config


def download_image(url, save_path):
    try:
        headers = {
            "User-Agent": config.USER_AGENT,
            "Referer": "https://www.baidu.com/"
        }
        response = requests.get(url, headers=headers, timeout=15, stream=True)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        if "image" not in content_type and not url.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
            return None

        ext = ".jpg"
        if "png" in content_type or url.lower().endswith(".png"):
            ext = ".png"
        elif "gif" in content_type or url.lower().endswith(".gif"):
            ext = ".gif"
        elif "webp" in content_type or url.lower().endswith(".webp"):
            ext = ".webp"

        final_path = save_path + ext
        os.makedirs(os.path.dirname(final_path), exist_ok=True)

        with open(final_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        file_size = os.path.getsize(final_path)
        if file_size < 1000:
            os.remove(final_path)
            return None

        return final_path
    except Exception as e:
        print(f"    图片下载失败: {e}")
        return None


def save_base64_image(b64_data, save_path):
    try:
        if "," in b64_data:
            b64_data = b64_data.split(",")[1]
        img_data = base64.b64decode(b64_data)
        final_path = save_path + ".png"
        os.makedirs(os.path.dirname(final_path), exist_ok=True)
        with open(final_path, "wb") as f:
            f.write(img_data)
        if os.path.getsize(final_path) < 1000:
            os.remove(final_path)
            return None
        return final_path
    except Exception as e:
        print(f"    Base64图片保存失败: {e}")
        return None


def is_valid_image_url(url):
    if not url:
        return False
    if url.startswith("data:"):
        return False
    exclude_patterns = ["logo", "icon", "avatar", "btn", "button", "ad.", "advert", "spacer", "pixel", "blank"]
    url_lower = url.lower()
    for pattern in exclude_patterns:
        if pattern in url_lower:
            return False
    return True


def search_images(keyword, max_results=5):
    images = []
    try:
        search_url = f"https://image.baidu.com/search/flip?tn=baiduimage&word={quote(keyword)}&pn=0"
        headers = {
            "User-Agent": config.USER_AGENT,
        }
        response = requests.get(search_url, headers=headers, timeout=15)
        response.encoding = "utf-8"

        img_urls = re.findall(r'"objURL":"(.*?)"', response.text)
        if not img_urls:
            img_urls = re.findall(r'"thumbURL":"(.*?)"', response.text)

        for url in img_urls[:max_results * 2]:
            if is_valid_image_url(url):
                images.append(url)
            if len(images) >= max_results:
                break
    except Exception as e:
        print(f"  图片搜索失败: {e}")

    return images


def generate_ai_image(prompt, size="1K", ratio="4:3"):
    """使用 Agnes Image 2.1 Flash 生成图片"""
    if not config.AI_API_KEY:
        print("  ✗ 未配置AI API密钥")
        return None
    try:
        base_url = getattr(config, 'AI_IMAGE_BASE_URL', config.AI_API_BASE_URL)
        model = getattr(config, 'AI_IMAGE_MODEL', 'agnes-image-2.1-flash')
        
        url = f"{base_url}/images/generations"
        headers = {
            "Authorization": f"Bearer {config.AI_API_KEY}",
            "Content-Type": "application/json",
        }
        data = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "ratio": ratio,
            "response_format": "b64_json"
        }
        
        print(f"  📡 调用图片API: {url}")
        print(f"  📝 提示词: {prompt[:50]}...")
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
        except requests.exceptions.SSLError:
            print(f"  ⚠️ SSL连接错误，尝试禁用SSL验证")
            response = requests.post(url, headers=headers, json=data, timeout=60, verify=False)
        
        print(f"  📤 响应状态: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
            except ValueError:
                print(f"  ✗ 响应不是有效的JSON")
                return None
                
            if result.get("data") and isinstance(result["data"], list) and len(result["data"]) > 0:
                item = result["data"][0]
                b64 = item.get("b64_json")
                if b64:
                    print("  ✓ 获取到Base64图片")
                    return b64
                img_url = item.get("url")
                if img_url:
                    print(f"  📥 下载图片: {img_url[:30]}...")
                    resp = requests.get(img_url, timeout=30)
                    resp.raise_for_status()
                    return base64.b64encode(resp.content).decode("utf-8")
                print(f"  ✗ 响应数据中没有图片数据: {item.keys()}")
            else:
                print(f"  ✗ 响应数据格式异常: {result.keys() if isinstance(result, dict) else '非字典'}")
        else:
            error_text = response.text[:200]
            print(f"  ✗ API调用失败 [{response.status_code}]: {error_text}")
            if "model_not_found" in error_text.lower():
                print(f"  💡 模型名可能有误，请检查配置: {model}")
            
    except Exception as e:
        print(f"  AI图片生成失败: {type(e).__name__} - {e}")
    return None


def build_image_prompt(article, category_id):
    """根据文章内容和栏目生成AI绘图提示词"""
    title = article.get("kid_title", article.get("title", ""))
    highlight = article.get("highlight", "")

    style_desc = "cartoon illustration for kids, bright vibrant colors, cute and friendly style, children's book illustration, simple and clean design"

    theme_keywords = {
        "headline": "exciting science discovery, amazing scene",
        "space": "outer space, rockets, planets, stars, astronauts, cosmos",
        "physics": "physics experiment, atoms, light beams, energy, laboratory",
        "chemistry": "chemistry lab, colorful liquids, test tubes, molecules, atoms",
        "tech": "robots, technology, futuristic, circuits, gadgets",
        "life": "nature, animals, plants, cells, DNA, biology",
        "earth": "earth, nature, environment, mountains, oceans, weather",
        "fun": "fun and curious, magical science, surprised expression",
        "scientist": "scientist character, lab coat, doing experiments",
        "experiment": "science experiment, hands-on, DIY, fun project",
    }

    theme = theme_keywords.get(category_id, "science and nature")

    prompt = f"{title}, {theme}, {style_desc}, high quality illustration"

    if highlight:
        prompt += f", main subject: {highlight}"

    return prompt


def get_article_image(article, category_id, issue_id):
    keyword = article.get("kid_title", article.get("title", ""))

    print(f"  🎨 尝试AI生成配图...")
    prompt = build_image_prompt(article, category_id)
    ai_b64 = generate_ai_image(prompt)
    if ai_b64:
        save_name = f"{issue_id}_{category_id}_ai"
        save_path = os.path.join(config.IMAGES_DIR, save_name)
        saved = save_base64_image(ai_b64, save_path)
        if saved:
            print(f"  ✓ AI生成配图成功")
            return os.path.relpath(saved, config.OUTPUT_DIR)

    if article.get("images") and len(article["images"]) > 0:
        for img_info in article["images"][:3]:
            img_url = img_info["url"]
            if is_valid_image_url(img_url):
                save_name = f"{issue_id}_{category_id}_src"
                save_path = os.path.join(config.IMAGES_DIR, save_name)
                downloaded = download_image(img_url, save_path)
                if downloaded:
                    print(f"  ✓ 使用原文配图")
                    return os.path.relpath(downloaded, config.OUTPUT_DIR)

    print(f"  搜索配图: {keyword[:20]}...")
    search_keyword = f"{keyword} 科普 插画"
    img_urls = search_images(search_keyword, max_results=5)

    for i, img_url in enumerate(img_urls):
        save_name = f"{issue_id}_{category_id}_{i}"
        save_path = os.path.join(config.IMAGES_DIR, save_name)
        downloaded = download_image(img_url, save_path)
        if downloaded:
            print(f"  ✓ 找到配图")
            return os.path.relpath(downloaded, config.OUTPUT_DIR)

    print(f"  ✗ 未找到合适配图")
    return None
