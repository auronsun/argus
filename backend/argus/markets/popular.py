"""Curated lists of widely-searched HK and A-share tickers.

Used by the search layer to resolve text queries (Chinese / English names)
without scanning the whole exchange every keystroke. Long-tail tickers
are still reachable by typing the numeric code directly — the search
adapter constructs the canonical symbol on the fly.

These lists cover the ~80-100 stocks that account for the overwhelming
majority of retail search volume; long-tail discovery is a separate
problem that doesn't belong in autocomplete.
"""
from __future__ import annotations


# (code, Chinese name, English name) — code is the bare digit-only form.
HK_POPULAR: list[tuple[str, str, str]] = [
    ("00700", "腾讯控股",     "Tencent Holdings"),
    ("09988", "阿里巴巴",     "Alibaba Group"),
    ("03690", "美团",         "Meituan"),
    ("01810", "小米集团",     "Xiaomi"),
    ("00941", "中国移动",     "China Mobile"),
    ("01299", "友邦保险",     "AIA Group"),
    ("00939", "建设银行",     "China Construction Bank"),
    ("00005", "汇丰控股",     "HSBC Holdings"),
    ("00388", "香港交易所",   "Hong Kong Exchanges"),
    ("01398", "工商银行",     "ICBC"),
    ("00857", "中国石油",     "PetroChina"),
    ("00883", "中国海洋石油", "CNOOC"),
    ("00386", "中国石化",     "Sinopec"),
    ("00762", "中国联通",     "China Unicom"),
    ("01928", "金沙中国",     "Sands China"),
    ("09618", "京东集团",     "JD.com"),
    ("00011", "恒生银行",     "Hang Seng Bank"),
    ("00002", "中电控股",     "CLP Holdings"),
    ("01024", "快手",         "Kuaishou"),
    ("00001", "长和",         "CK Hutchison"),
    ("00027", "银河娱乐",     "Galaxy Entertainment"),
    ("00016", "新鸿基地产",   "Sun Hung Kai Properties"),
    ("01113", "长实集团",     "CK Asset Holdings"),
    ("09999", "网易",         "NetEase"),
    ("06862", "海底捞",       "Haidilao"),
    ("02318", "中国平安",     "Ping An Insurance"),
    ("00066", "港铁公司",     "MTR Corporation"),
    ("01093", "石药集团",     "CSPC Pharmaceutical"),
    ("00823", "领展房产基金", "Link REIT"),
    ("00017", "新世界发展",   "New World Development"),
    ("01880", "中国中免",     "China Tourism Group"),
    ("01378", "中国宏桥",     "China Hongqiao"),
    ("06160", "百济神州",     "BeiGene"),
    ("09888", "百度集团",     "Baidu"),
    ("01211", "比亚迪股份",   "BYD"),
    ("00992", "联想集团",     "Lenovo"),
    ("00291", "华润啤酒",     "China Resources Beer"),
    ("00285", "比亚迪电子",   "BYD Electronic"),
    ("01972", "太古地产",     "Swire Properties"),
    ("00019", "太古股份公司A","Swire Pacific A"),
    ("01801", "信达生物",     "Innovent Biologics"),
    ("06618", "京东健康",     "JD Health"),
    ("06098", "华润万象生活", "China Resources Mixc"),
    ("00322", "康师傅控股",   "Tingyi"),
    ("00288", "万洲国际",     "WH Group"),
    ("06837", "海通证券",     "Haitong Securities"),
    ("01258", "中国有色矿业", "China Nonferrous Mining"),
    ("01033", "中石化油服",   "Sinopec Oilfield Service"),
    ("01171", "兖矿能源",     "Yankuang Energy"),
    ("01088", "中国神华",     "China Shenhua"),
    ("01658", "邮储银行",     "Postal Savings Bank"),
    ("03988", "中国银行",     "Bank of China"),
    ("00688", "中国海外发展", "China Overseas Land"),
    ("00688", "中国海外发展", "China Overseas Land"),
    ("00270", "粤海投资",     "Guangdong Investment"),
    ("00669", "创科实业",     "Techtronic Industries"),
    ("01177", "中国生物制药", "Sino Biopharmaceutical"),
    ("01038", "长江基建集团", "CK Infrastructure"),
    ("00012", "恒基地产",     "Henderson Land"),
    ("01918", "融创中国",     "Sunac China"),
    ("00788", "中国铁塔",     "China Tower"),
    ("01658", "邮储银行",     "Postal Savings Bank"),
    ("00868", "信义玻璃",     "Xinyi Glass"),
    ("00027", "银河娱乐",     "Galaxy Entertainment"),
    ("01997", "九龙仓置业",   "Wharf REIC"),
]


CN_POPULAR: list[tuple[str, str, str]] = [
    ("600519", "贵州茅台",   "Kweichow Moutai"),
    ("000858", "五粮液",     "Wuliangye Yibin"),
    ("601318", "中国平安",   "Ping An Insurance"),
    ("600036", "招商银行",   "China Merchants Bank"),
    ("000333", "美的集团",   "Midea Group"),
    ("002594", "比亚迪",     "BYD Company"),
    ("300750", "宁德时代",   "CATL"),
    ("601012", "隆基绿能",   "LONGi Green Energy"),
    ("002475", "立讯精密",   "Luxshare Precision"),
    ("600276", "恒瑞医药",   "Jiangsu Hengrui Pharma"),
    ("000001", "平安银行",   "Ping An Bank"),
    ("600028", "中国石化",   "Sinopec"),
    ("601899", "紫金矿业",   "Zijin Mining"),
    ("600030", "中信证券",   "CITIC Securities"),
    ("601398", "工商银行",   "ICBC"),
    ("600000", "浦发银行",   "SPD Bank"),
    ("600009", "上海机场",   "Shanghai Airport"),
    ("601166", "兴业银行",   "Industrial Bank"),
    ("002415", "海康威视",   "Hikvision"),
    ("002714", "牧原股份",   "Muyuan Foods"),
    ("601888", "中国中免",   "China Tourism Group"),
    ("601628", "中国人寿",   "China Life"),
    ("600900", "长江电力",   "China Yangtze Power"),
    ("601988", "中国银行",   "Bank of China"),
    ("601939", "建设银行",   "China Construction Bank"),
    ("601288", "农业银行",   "Agricultural Bank of China"),
    ("601857", "中国石油",   "PetroChina"),
    ("601668", "中国建筑",   "China State Construction"),
    ("600660", "福耀玻璃",   "Fuyao Glass"),
    ("002352", "顺丰控股",   "SF Holding"),
    ("300059", "东方财富",   "East Money Information"),
    ("300760", "迈瑞医疗",   "Shenzhen Mindray"),
    ("002230", "科大讯飞",   "iFlytek"),
    ("300015", "爱尔眼科",   "Aier Eye Hospital"),
    ("600585", "海螺水泥",   "Anhui Conch Cement"),
    ("600406", "国电南瑞",   "NARI Technology"),
    ("002271", "东方雨虹",   "Beijing Oriental Yuhong"),
    ("601138", "工业富联",   "Foxconn Industrial Internet"),
    ("002460", "赣锋锂业",   "Ganfeng Lithium"),
    ("600436", "片仔癀",     "Pien Tze Huang"),
    ("600196", "复星医药",   "Shanghai Fosun Pharma"),
    ("601877", "正泰电器",   "Zhejiang Chint Electrics"),
    ("300124", "汇川技术",   "Inovance Technology"),
    ("002241", "歌尔股份",   "Goertek"),
    ("603259", "药明康德",   "WuXi AppTec"),
    ("603501", "韦尔股份",   "Will Semiconductor"),
    ("002007", "华兰生物",   "Hualan Biological"),
    ("600886", "国投电力",   "SDIC Power"),
    ("688256", "寒武纪",     "Cambricon Technologies"),
    ("688981", "中芯国际",   "SMIC"),
    ("688111", "金山办公",   "Beijing Kingsoft Office"),
    ("688041", "海光信息",   "Hygon Information"),
]


def _normalise(text: str) -> str:
    return (text or "").strip().lower()


def search_hk(query: str, limit: int = 10) -> list[tuple[str, str]]:
    """Return (code, display_name) pairs matching the query.

    Match rules:
      - All digits: prefix match against code (with leading zeros stripped).
      - Otherwise: substring match against either Chinese or English name.
    """
    return _search(HK_POPULAR, query, limit)


def search_cn(query: str, limit: int = 10) -> list[tuple[str, str]]:
    return _search(CN_POPULAR, query, limit)


def _search(table: list[tuple[str, str, str]], query: str, limit: int) -> list[tuple[str, str]]:
    q = (query or "").strip()
    if not q:
        return []
    if q.isdigit():
        target = q.lstrip("0") or "0"
        out: list[tuple[str, str]] = []
        seen: set[str] = set()
        for code, zh, en in table:
            if code in seen:
                continue
            stripped = code.lstrip("0") or "0"
            if stripped.startswith(target):
                seen.add(code)
                out.append((code, f"{zh} / {en}"))
                if len(out) >= limit:
                    break
        return out

    needle = _normalise(q)
    out2: list[tuple[str, str]] = []
    seen2: set[str] = set()
    for code, zh, en in table:
        if code in seen2:
            continue
        if needle in _normalise(zh) or needle in _normalise(en):
            seen2.add(code)
            out2.append((code, f"{zh} / {en}"))
            if len(out2) >= limit:
                break
    return out2
