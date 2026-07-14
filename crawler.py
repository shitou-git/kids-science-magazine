import hashlib
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

import config


def get_headers():
    return {
        "User-Agent": config.USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }


def fetch_url(url, encoding="utf-8"):
    for attempt in range(config.MAX_RETRIES):
        try:
            response = requests.get(
                url,
                headers=get_headers(),
                timeout=config.REQUEST_TIMEOUT,
                allow_redirects=True
            )
            response.raise_for_status()
            response.encoding = encoding
            return response.text
        except Exception as e:
            if attempt == config.MAX_RETRIES - 1:
                print(f"抓取失败 {url}: {e}")
                return None
    return None


def extract_text_from_html(html_content):
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def extract_article_images(html_content, base_url):
    if not html_content:
        return []
    soup = BeautifulSoup(html_content, "lxml")
    images = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-original")
        if src:
            try:
                full_url = urljoin(base_url, src)
                if full_url.startswith(("http://", "https://")):
                    alt = img.get("alt", "")
                    images.append({"url": full_url, "alt": alt})
            except Exception:
                pass
    return images[:5]


def is_valid_article(title, content):
    if not title or not content:
        return False
    if len(title) < 5 or len(content) < 100:
        return False
    if re.search(r"广告|推广|优惠|点击|下载|注册", title):
        return False
    # 检查是否含有不适合少儿的内容
    full_text = title + " " + content[:500]
    for keyword in config.INAPPROPRIATE_KEYWORDS:
        if keyword in full_text:
            return False
    return True


def kid_friendly_score(title, content):
    """计算文章的少儿友好度评分"""
    text = (title + " " + content[:1000]).lower()
    score = 0
    for keyword in config.KID_FRIENDLY_KEYWORDS:
        if keyword.lower() in text:
            score += 1
    # 标题中包含少儿友好词额外加分
    title_lower = title.lower()
    for keyword in config.KID_FRIENDLY_KEYWORDS:
        if keyword.lower() in title_lower:
            score += 2
    # 文章长度适中加分（200-800字为佳）
    content_len = len(content)
    if 200 <= content_len <= 800:
        score += 3
    elif 800 < content_len <= 2000:
        score += 1
    # 过长的文章可能不适合（学术性太强）
    if content_len > 3000:
        score -= 2
    return score


def content_hash(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def parse_date_text(date_str):
    """从各种中文日期格式中解析出datetime对象"""
    if not date_str:
        return None
    date_str = date_str.strip()

    # 尝试多种中文日期格式
    patterns = [
        r"(\d{4})年(\d{1,2})月(\d{1,2})日",
        r"(\d{4})-(\d{1,2})-(\d{1,2})",
        r"(\d{4})/(\d{1,2})/(\d{1,2})",
        r"(\d{4})\.(\d{1,2})\.(\d{1,2})",
    ]
    for pattern in patterns:
        m = re.search(pattern, date_str)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                continue

    # 尝试ISO格式
    try:
        clean = date_str.replace("Z", "+00:00").replace("+08:00", "")
        # 截取前19位避免时区问题
        if len(clean) >= 10:
            return datetime.fromisoformat(clean[:19])
    except Exception:
        pass

    return None


def is_within_week(date_str):
    if not date_str:
        return True  # 无法解析日期时，先保留，靠后续评分筛选
    article_date = parse_date_text(date_str)
    if not article_date:
        return True
    one_week_ago = datetime.now() - timedelta(days=7)
    return article_date >= one_week_ago


def parse_date_from_soup(soup):
    date_selectors = [
        "meta[property='article:published_time']",
        "meta[name='pubdate']",
        "meta[name='publishdate']",
        "time[datetime]",
        ".time",
        ".date",
        ".pub-time",
        ".publish-time",
    ]
    for selector in date_selectors:
        element = soup.select_one(selector)
        if element:
            date_str = element.get("content") or element.get("datetime") or element.get_text(strip=True)
            if date_str:
                return date_str
    return None


def find_article_links(html_content, base_url, max_links=20):
    if not html_content:
        return []
    soup = BeautifulSoup(html_content, "lxml")
    links = []
    seen_urls = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        try:
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            if parsed.scheme not in ("http", "https"):
                continue
            if full_url in seen_urls:
                continue
            title = a_tag.get_text(strip=True)
            if len(title) < 6:
                continue
            path = parsed.path
            if re.search(r"/(article|news|info|detail|content|story|post|kepu)/|/\d{4}/\d{2}/|/\d+\.s?html?", path):
                links.append({"url": full_url, "title": title})
                seen_urls.add(full_url)
                if len(links) >= max_links:
                    break
        except Exception:
            continue

    return links


def scrape_article(url, encoding="utf-8"):
    html = fetch_url(url, encoding)
    if not html:
        return None

    soup = BeautifulSoup(html, "lxml")

    title = ""
    title_tag = soup.find("h1")
    if title_tag:
        title = title_tag.get_text(strip=True)
    if not title:
        title_meta = soup.find("meta", property="og:title")
        if title_meta:
            title = title_meta.get("content", "")
    if not title:
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)

    content = ""
    content_selectors = [
        "article",
        ".article-content",
        ".article-body",
        ".content",
        ".post-content",
        ".news-content",
        "#content",
        ".text",
        ".detail",
    ]
    for selector in content_selectors:
        content_tag = soup.select_one(selector)
        if content_tag and len(content_tag.get_text(strip=True)) > 200:
            content = content_tag.get_text(separator="\n", strip=True)
            break

    if not content:
        content = extract_text_from_html(html)

    publish_date = parse_date_from_soup(soup)

    images = extract_article_images(html, url)

    if not is_valid_article(title, content):
        return None

    score = kid_friendly_score(title, content)

    return {
        "title": title,
        "content": content,
        "url": url,
        "images": images,
        "publish_date": publish_date,
        "hash": content_hash(title + content[:500]),
        "kid_score": score,
    }


def collect_news():
    all_articles = []
    seen_hashes = set()

    # 按优先级排序信息源（少儿专属源优先）
    sources = sorted(config.NEWS_SOURCES, key=lambda s: s.get("priority", 0), reverse=True)

    for source in sources:
        print(f"\n正在采集: {source['name']} - {source['url']}")
        try:
            html = fetch_url(source["url"], source.get("encoding", "utf-8"))
            if not html:
                continue

            article_links = find_article_links(html, source["url"], config.MAX_ARTICLES_PER_SOURCE)
            print(f"  找到 {len(article_links)} 个文章链接")

            for link in article_links[:15]:
                try:
                    article = scrape_article(link["url"], source.get("encoding", "utf-8"))
                    if article and article["hash"] not in seen_hashes:
                        if is_within_week(article.get("publish_date")):
                            article["source"] = source["name"]
                            all_articles.append(article)
                            seen_hashes.add(article["hash"])
                            print(f"  ✓ 采集: {article['title'][:30]}... [少儿友好分: {article['kid_score']}]")
                except Exception as e:
                    print(f"  ✗ 文章抓取失败: {e}")
                    continue
        except Exception as e:
            print(f"  采集失败: {e}")
            continue

    # 按少儿友好度排序，过滤掉低分文章
    all_articles = [a for a in all_articles if a["kid_score"] >= config.MIN_KID_FRIENDLY_SCORE]
    all_articles.sort(key=lambda a: a["kid_score"], reverse=True)

    print(f"\n共采集到 {len(all_articles)} 篇有效文章（已按少儿友好度排序）")
    for i, a in enumerate(all_articles[:10]):
        print(f"  Top{i+1} [分:{a['kid_score']}] {a['title'][:40]}...")

    return all_articles
