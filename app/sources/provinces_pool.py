"""
全国 31 省市官方招考、卫健委及各级疾控中心（CDC）源扩展池
涵盖各省人力资源与社会保障厅、卫生健康委员会、中国疾控及各省级疾控中心、官方人事考试网
"""
from typing import Dict, Any, List

PROVINCE_SOURCES: List[Dict[str, Any]] = [
    # 国家级及重点省级疾控中心
    {"code": "chinacdc_official", "name": "中国疾病预防控制中心", "province": "全国", "url": "https://www.chinacdc.cn", "category": "国家级疾控/官方"},
    {"code": "beijing_cdc", "name": "北京市疾病预防控制中心", "province": "北京市", "url": "https://www.bjcdc.org", "category": "省级疾控/官方"},
    {"code": "guangdong_cdc", "name": "广东省疾病预防控制中心", "province": "广东省", "url": "http://cdcp.gd.gov.cn", "category": "省级疾控/官方"},
    {"code": "shanghai_cdc", "name": "上海市疾病预防控制中心", "province": "上海市", "url": "https://www.scdc.sh.cn", "category": "省级疾控/官方"},
    {"code": "jiangsu_cdc", "name": "江苏省疾病预防控制中心", "province": "江苏省", "url": "http://www.jscdc.cn", "category": "省级疾控/官方"},
    {"code": "zhejiang_cdc", "name": "浙江省疾病预防控制中心", "province": "浙江省", "url": "https://www.cdc.zj.cn", "category": "省级疾控/官方"},
    {"code": "shandong_cdc", "name": "山东省疾病预防控制中心", "province": "山东省", "url": "http://www.sdcdc.cn", "category": "省级疾控/官方"},
    {"code": "hubei_cdc", "name": "湖北省疾病预防控制中心", "province": "湖北省", "url": "https://www.hbcdc.com", "category": "省级疾控/官方"},
    {"code": "sichuan_cdc", "name": "四川省疾病预防控制中心", "province": "四川省", "url": "http://www.sccdpc.gov.cn", "category": "省级疾控/官方"},
    {"code": "chongqing_cdc", "name": "重庆市疾病预防控制中心", "province": "重庆市", "url": "http://www.cqcdc.org", "category": "省级疾控/官方"},
    {"code": "guizhou_cdc", "name": "贵州省疾病预防控制中心", "province": "贵州省", "url": "http://www.gzcdc.gov.cn", "category": "省级疾控/官方"},
    {"code": "yunnan_cdc", "name": "云南省疾病预防控制中心", "province": "云南省", "url": "http://www.yncdc.cn", "category": "省级疾控/官方"},
    {"code": "guangxi_cdc", "name": "广西壮族自治区疾病预防控制中心", "province": "广西壮族自治区", "url": "http://www.gxcdc.com", "category": "省级疾控/官方"},
    {"code": "hainan_cdc", "name": "海南省疾病预防控制中心", "province": "海南省", "url": "http://www.hncdc.cn", "category": "省级疾控/官方"},
    {"code": "liaoning_cdc", "name": "辽宁省疾病预防控制中心", "province": "辽宁省", "url": "http://www.lncdc.com.cn", "category": "省级疾控/官方"},
    {"code": "jilin_cdc", "name": "吉林省疾病预防控制中心", "province": "吉林省", "url": "http://www.jlcdc.com.cn", "category": "省级疾控/官方"},
    {"code": "heilongjiang_cdc", "name": "黑龙江省疾病预防控制中心", "province": "黑龙江省", "url": "http://www.hljcdc.org.cn", "category": "省级疾控/官方"},
    {"code": "henan_cdc", "name": "河南省疾病预防控制中心", "province": "河南省", "url": "http://www.hncdc.com.cn", "category": "省级疾控/官方"},
    {"code": "hunan_cdc", "name": "湖南省疾病预防控制中心", "province": "湖南省", "url": "http://www.hncdc.com", "category": "省级疾控/官方"},
    {"code": "anhui_cdc", "name": "安徽省疾病预防控制中心", "province": "安徽省", "url": "http://www.ahcdc.cn", "category": "省级疾控/官方"},
    {"code": "fujian_cdc", "name": "福建省疾病预防控制中心", "province": "福建省", "url": "http://www.fjcdc.com.cn", "category": "省级疾控/官方"},
    {"code": "shaanxi_cdc", "name": "陕西省疾病预防控制中心", "province": "陕西省", "url": "http://www.sxcdc.com", "category": "省级疾控/官方"},
    {"code": "hebei_cdc", "name": "河北省疾病预防控制中心", "province": "河北省", "url": "http://www.hebicdc.cn", "category": "省级疾控/官方"},
    {"code": "shanxi_cdc", "name": "山西省疾病预防控制中心", "province": "山西省", "url": "http://www.sxcdc.cn", "category": "省级疾控/官方"},
    {"code": "jiangxi_cdc", "name": "江西省疾病预防控制中心", "province": "江西省", "url": "http://www.jxcde.com", "category": "省级疾控/官方"},

    # 华东地区
    {"code": "zhejiang_wsjkw", "name": "浙江省卫生健康委员会", "province": "浙江省", "url": "https://wsjkw.zj.gov.cn", "category": "卫健委/官方"},
    {"code": "jiangsu_rsks", "name": "江苏省人事考试网", "province": "江苏省", "url": "http://jshrss.jiangsu.gov.cn/col/col57210/index.html", "category": "人事考试网"},
    {"code": "jiangsu_wsjkw", "name": "江苏省卫生健康委员会", "province": "江苏省", "url": "http://wjw.jiangsu.gov.cn", "category": "卫健委/官方"},
    {"code": "shanghai_rsj", "name": "上海市人力资源和社会保障局", "province": "上海市", "url": "https://rsj.sh.gov.cn", "category": "人社局/官方"},
    {"code": "anhui_wsjkw", "name": "安徽省卫生健康委员会", "province": "安徽省", "url": "http://wjw.ah.gov.cn", "category": "卫健委/官方"},
    {"code": "fujian_rsks", "name": "福建省人事考试网", "province": "福建省", "url": "http://www.fjkl.gov.cn", "category": "人事考试网"},
    {"code": "shandong_wsjkw", "name": "山东省卫生健康委员会", "province": "山东省", "url": "http://wsjkw.shandong.gov.cn", "category": "卫健委/官方"},
    {"code": "jiangxi_rsks", "name": "江西人事考试网", "province": "江西省", "url": "http://www.jxpta.com", "category": "人事考试网"},

    # 华北地区
    {"code": "beijing_rsj", "name": "北京市人力资源和社会保障局", "province": "北京市", "url": "http://rsj.beijing.gov.cn", "category": "人社局/官方"},
    {"code": "beijing_wsjkw", "name": "北京市卫生健康委员会", "province": "北京市", "url": "http://wjw.beijing.gov.cn", "category": "卫健委/官方"},
    {"code": "tianjin_rsks", "name": "天津市人才考评中心", "province": "天津市", "url": "http://hrss.tj.gov.cn/jsdw/rsksw", "category": "人事考试网"},
    {"code": "hebei_wsjkw", "name": "河北省卫生健康委员会", "province": "河北省", "url": "http://wsjkw.hebei.gov.cn", "category": "卫健委/官方"},
    {"code": "shanxi_wsjkw", "name": "山西省卫生健康委员会", "province": "山西省", "url": "http://wjw.shanxi.gov.cn", "category": "卫健委/官方"},
    {"code": "neimenggu_rsks", "name": "内蒙古人事考试网", "province": "内蒙古自治区", "url": "http://www.impta.com.cn/sydw/index.asp", "category": "人事考试网"},

    # 华南地区
    {"code": "guangdong_wsjkw", "name": "广东省卫生健康委员会", "province": "广东省", "url": "http://wsjkw.gd.gov.cn", "category": "卫健委/官方"},
    {"code": "guangxi_rsks", "name": "广西人事考试网", "province": "广西壮族自治区", "url": "http://www.gxpta.com.cn", "category": "人事考试网"},
    {"code": "hainan_wsjkw", "name": "海南省卫生健康委员会", "province": "海南省", "url": "http://wst.hainan.gov.cn", "category": "卫健委/官方"},

    # 华中地区
    {"code": "henan_wsjkw", "name": "河南省卫生健康委员会", "province": "河南省", "url": "http://wsjkw.henan.gov.cn", "category": "卫健委/官方"},
    {"code": "hubei_rsks", "name": "湖北省人事考试网", "province": "湖北省", "url": "http://www.hbsrsksy.cn", "category": "人事考试网"},
    {"code": "hubei_wsjkw", "name": "湖北省卫生健康委员会", "province": "湖北省", "url": "http://wjw.hubei.gov.cn", "category": "卫健委/官方"},
    {"code": "hunan_wsjkw", "name": "湖南省卫生健康委员会", "province": "湖南省", "url": "http://wjw.hunan.gov.cn", "category": "卫健委/官方"},

    # 西南地区
    {"code": "sichuan_rsks", "name": "四川省人力资源和社会保障厅-人事考试", "province": "四川省", "url": "http://www.scpta.com.cn", "category": "人事考试网"},
    {"code": "sichuan_wsjkw", "name": "四川省卫生健康委员会", "province": "四川省", "url": "http://wsjkw.sc.gov.cn", "category": "卫健委/官方"},
    {"code": "chongqing_rsks", "name": "重庆市人力资源和社会保障局", "province": "重庆市", "url": "http://rlsbj.cq.gov.cn", "category": "人社局/官方"},
    {"code": "guizhou_wsjkw", "name": "贵州省卫生健康委员会", "province": "贵州省", "url": "http://wjw.guizhou.gov.cn", "category": "卫健委/官方"},
    {"code": "yunnan_rsks", "name": "云南省人事考试院", "province": "云南省", "url": "http://www.ynrsksw.com", "category": "人事考试网"},
    {"code": "yunnan_wsjkw", "name": "云南省卫生健康委员会", "province": "云南省", "url": "http://ynswsjkw.yn.gov.cn", "category": "卫健委/官方"},
    {"code": "xizang_rsks", "name": "西藏自治区人力资源和社会保障厅", "province": "西藏自治区", "url": "http://hrss.xizang.gov.cn", "category": "人社局/官方"},

    # 西北地区
    {"code": "shaanxi_wsjkw", "name": "陕西省卫生健康委员会", "province": "陕西省", "url": "http://sxwjw.shaanxi.gov.cn", "category": "卫健委/官方"},
    {"code": "gansu_rsks", "name": "甘肃省人力资源和社会保障厅", "province": "甘肃省", "url": "http://rst.gansu.gov.cn", "category": "人社局/官方"},
    {"code": "qinghai_wsjkw", "name": "青海省卫生健康委员会", "province": "青海省", "url": "https://wsjkw.qinghai.gov.cn", "category": "卫健委/官方"},
    {"code": "ningxia_rsks", "name": "宁夏人事考试中心", "province": "宁夏回族自治区", "url": "https://www.nxpta.com", "category": "人事考试网"},
    {"code": "xinjiang_rsks", "name": "新疆人事考试中心", "province": "新疆维望尔自治区", "url": "http://www.xjrsks.com.cn", "category": "人事考试网"},

    # 东北地区
    {"code": "liaoning_wsjkw", "name": "辽宁省卫生健康委员会", "province": "辽宁省", "url": "https://wsjk.ln.gov.cn", "category": "卫健委/官方"},
    {"code": "jilin_wsjkw", "name": "吉林省卫生健康委员会", "province": "吉林省", "url": "http://wsjkw.jl.gov.cn", "category": "卫健委/官方"},
    {"code": "heilongjiang_rsks", "name": "黑龙江省人事考试网", "province": "黑龙江省", "url": "http://www.hljrsks.org.cn", "category": "人事考试网"}
]

PROVINCES_SOURCE_POOL = PROVINCE_SOURCES

def get_all_province_sources() -> List[Dict[str, Any]]:
    """获取全国 31 省市官方采集源清单"""
    return PROVINCE_SOURCES
