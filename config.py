import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

AI_API_BASE_URL = "https://api.chatlz.dpdns.org/v1"
AI_API_KEY = os.environ.get("AGENS_AI_API_KEY", "sk-chatlz-proxy")
AI_MODEL = "agnes-2.0-flash"

AI_IMAGE_BASE_URL = "https://lmage.chatlz.dpdns.org/v1"
AI_IMAGE_MODEL = "agnes-image-2.1-flash"

SCHEDULE_DAY = "friday"
SCHEDULE_TIME = "20:00"

OUTPUT_DIR = os.path.join(BASE_DIR, "output")
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
ARCHIVE_DIR = os.path.join(OUTPUT_DIR, "archive")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

CATEGORIES = [
    {
        "id": "headline",
        "name": "头版头条",
        "icon": "🌟",
        "keywords": ["重大", "突破", "首次", "发现", "里程碑", "震惊", "重磅", "头条", "热点", "新闻"]
    },
    {
        "id": "hero",
        "name": "榜样力量",
        "icon": "⭐",
        "keywords": ["榜样", "英雄", "先锋", "模范", "感动", "人物", "事迹", "奋斗", "坚持", "努力", "成就", "贡献", "科学家", "工程师", "宇航员", "冠军"]
    },
    {
        "id": "china",
        "name": "中国故事",
        "icon": "🇨🇳",
        "keywords": ["中国", "祖国", "国内", "科技", "航天", "工程", "建设", "成就", "发展", "创新", "突破", "制造", "研发", "技术", "高铁", "航天", "量子", "人工智能", "新能源"]
    },
    {
        "id": "world",
        "name": "多元世界",
        "icon": "🌍",
        "keywords": ["世界", "国际", "全球", "外国", "海外", "美国", "欧洲", "日本", "科技", "航天", "文化", "新闻", "事件", "发现", "探索"]
    },
    {
        "id": "science",
        "name": "科学创新",
        "icon": "🔬",
        "keywords": ["科学", "创新", "研究", "发现", "实验", "技术", "发明", "前沿", "突破", "探索", "物理", "化学", "生物", "天文", "数学", "工程"]
    },
    {
        "id": "culture",
        "name": "文化之旅",
        "icon": "🎨",
        "keywords": ["文化", "历史", "艺术", "传统", "节日", "非遗", "文物", "古迹", "考古", "绘画", "音乐", "文学", "建筑", "风俗"]
    },
    {
        "id": "nature",
        "name": "趣味自然",
        "icon": "🌿",
        "keywords": ["自然", "动物", "植物", "海洋", "森林", "昆虫", "鸟类", "恐龙", "生态", "环境", "天气", "气候", "奇观", "神奇", "有趣", "冷知识"]
    },
    {
        "id": "fun",
        "name": "漫画乐园",
        "icon": "🎭",
        "keywords": ["漫画", "动画", "搞笑", "有趣", "故事", "幽默", "开心", "欢乐", "卡通", "图画", "趣味", "轻松"]
    }
]

NEWS_SOURCES = [
    # 综合科普源（优先级最高）
    {
        "name": "科普中国",
        "url": "https://www.kepuchina.cn/",
        "type": "general",
        "encoding": "utf-8",
        "priority": 3
    },
    {
        "name": "科普中国-科技前沿",
        "url": "https://www.kepuchina.cn/kejqy/",
        "type": "general",
        "encoding": "utf-8",
        "priority": 2
    },
    {
        "name": "科普中国-百科探秘",
        "url": "https://www.kepuchina.cn/kpcidian/",
        "type": "general",
        "encoding": "utf-8",
        "priority": 2
    },
    # 科学网
    {
        "name": "科学网",
        "url": "https://www.sciencenet.cn/",
        "type": "general",
        "encoding": "utf-8",
        "priority": 2
    },
    {
        "name": "科学网-科普",
        "url": "https://news.sciencenet.cn/sciencenews.aspx?id=1",
        "type": "general",
        "encoding": "utf-8",
        "priority": 1
    },
    # 中国数字科技馆
    {
        "name": "中国数字科技馆",
        "url": "https://www.cdstm.cn/",
        "type": "general",
        "encoding": "utf-8",
        "priority": 2
    },
    # 果壳网（高质量科普，适合青少年）
    {
        "name": "果壳网",
        "url": "https://www.guokr.com/scientific/",
        "type": "general",
        "encoding": "utf-8",
        "priority": 3
    },
    {
        "name": "果壳-物种日历",
        "url": "https://www.guokr.com/calendar/",
        "type": "general",
        "encoding": "utf-8",
        "priority": 2
    },
    # 中科院科普
    {
        "name": "中科院科普",
        "url": "https://www.cas.cn/kx/",
        "type": "general",
        "encoding": "utf-8",
        "priority": 2
    },
    # 中国航天科普网
    {
        "name": "中国航天科普网",
        "url": "https://www.spacechina.com/n25/n148/",
        "type": "general",
        "encoding": "utf-8",
        "priority": 2
    },
    # 中国国家地理（博物杂志）
    {
        "name": "中国国家地理",
        "url": "https://www.dili360.com/",
        "type": "general",
        "encoding": "utf-8",
        "priority": 2
    },
    # 国家自然博物馆
    {
        "name": "国家自然博物馆",
        "url": "https://www.nnhm.org.cn/",
        "type": "general",
        "encoding": "utf-8",
        "priority": 2
    },
    # 中国科技馆
    {
        "name": "中国科技馆",
        "url": "https://www.cstm.org.cn/",
        "type": "general",
        "encoding": "utf-8",
        "priority": 1
    },
    # 人民网科普
    {
        "name": "人民网科普",
        "url": "http://scitech.people.com.cn/GB/1057/index.html",
        "type": "general",
        "encoding": "utf-8",
        "priority": 2
    },
    # 光明网科普
    {
        "name": "光明网科普",
        "url": "https://tech.gmw.cn/",
        "type": "general",
        "encoding": "utf-8",
        "priority": 2
    },
    # 中国天气网科普
    {
        "name": "中国天气网科普",
        "url": "http://www.weather.com.cn/",
        "type": "general",
        "encoding": "utf-8",
        "priority": 1
    },
]

# 少儿不适合内容过滤关键词（标题或内容含这些词则跳过）
INAPPROPRIATE_KEYWORDS = [
    "色情", "暴力", "赌博", "毒品", "自杀",
    "政治敏感", "负面", "灾难", "死亡",
    "股市", "基金", "理财", "投资", "房价",
    "网游", "充值", "会员", "广告", "推广",
    "婚恋", "出轨", "离婚",
    "手术", "癌症", "肿瘤",
]

# 少儿友好内容加分关键词
KID_FRIENDLY_KEYWORDS = [
    "动物", "植物", "恐龙", "宇宙", "星球", "太阳", "月亮", "星星",
    "海洋", "森林", "昆虫", "鸟类", "天气", "彩虹", "火山", "地震",
    "机器人", "太空", "火箭", "卫星", "宇航员", "飞船",
    "实验", "发明", "发现", "探索", "冒险",
    "趣味", "神奇", "奇妙", "为什么", "秘密",
    "大脑", "心脏", "骨骼", "五感", "视觉", "听觉",
    "基因", "DNA", "进化", "物种",
    "环保", "节能", "回收", "绿色",
    "极光", "北极", "南极", "冰川", "沙漠",
    "历史", "古文明", "化石", "考古",
]

# 文章最低少儿友好分（低于此分则跳过）
MIN_KID_FRIENDLY_SCORE = 1

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

ARTICLES_PER_CATEGORY = 1
MAX_ARTICLES_PER_SOURCE = 20
