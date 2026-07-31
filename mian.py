from fastapi import FastAPI, Query
import requests
import re

app = FastAPI(title="A股数据 API 服务")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_symbol(symbol: str) -> str:
    """提取纯数字股票代码并自动加上 sh/sz 前缀"""
    # 提取字符串中的 6 位数字
    match = re.search(r'\d{6}', symbol)
    if not match:
        return symbol
    code = match.group(0)
    prefix = "sh" if code.startswith("6") or code.startswith("9") else "sz"
    return f"{prefix}{code}"

@app.get("/stock_spot")
def get_stock_spot(symbol: str = Query(..., description="6位股票代码，如 002891 或 002891.SZ")):
    """获取股票实时行情"""
    try:
        full_symbol = clean_symbol(symbol)
        url = f"http://qt.gtimg.cn/q={full_symbol}"
        
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.encoding = 'gbk'
        text = res.text
        
        if text and "~" in text:
            parts = text.split("~")
            if len(parts) > 30:
                return {
                    "status": "success",
                    "symbol": symbol,
                    "data": {
                        "股票名称": parts[1],
                        "股票代码": parts[2],
                        "最新价": float(parts[3]),
                        "昨收价": float(parts[4]),
                        "今开价": float(parts[5]),
                        "成交量(手)": int(parts[6]),
                        "涨跌额": float(parts[31]),
                        "涨跌幅(%)": float(parts[32]),
                        "最高价": float(parts[33]),
                        "最低价": float(parts[34]),
                        "成交额(万)": float(parts[37])
                    }
                }
        return {"status": "error", "message": f"未查询到股票 {symbol} 的数据"}
    except Exception as e:
        return {"status": "error", "message": f"请求失败: {str(e)}"}

@app.get("/stock_history")
def get_stock_history(
    symbol: str = Query(..., description="6位股票代码"),
    count: int = Query(30, description="获取的历史天数")
):
    """获取股票历史日线 K 线数据（包含任意历史天数及每日涨跌幅）"""
    try:
        full_symbol = clean_symbol(symbol)
        url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={full_symbol},day,,,{count},qfq"
        res = requests.get(url, headers=HEADERS, timeout=10)
        data = res.json()
        
        stock_data = data.get("data", {}).get(full_symbol, {})
        # 兼容处理：腾讯可能返回 day 或 qfqday
        day_klines = stock_data.get("day") or stock_data.get("qfqday", [])
        
        history_list = []
        prev_close = None
        
        for item in day_klines:
            close_price = float(item[2])
            pct_change = 0.0
            if prev_close and prev_close > 0:
                pct_change = round(((close_price - prev_close) / prev_close) * 100, 2)
            prev_close = close_price
            
            history_list.append({
                "日期": item[0],
                "开盘价": float(item[1]),
                "收盘价": close_price,
                "最高价": float(item[3]),
                "最低价": float(item[4]),
                "成交量(手)": float(item[5]),
                "涨跌幅(%)": pct_change
            })
            
        return {"status": "success", "symbol": symbol, "count": len(history_list), "data": history_list}
    except Exception as e:
        return {"status": "error", "message": f"历史行情获取失败: {str(e)}"}

@app.get("/stock_financial")
def get_stock_financial(symbol: str = Query(..., description="6位股票代码")):
    """财务概况"""
    return get_stock_spot(symbol)

@app.get("/stock_money_flow")
def get_stock_money_flow(symbol: str = Query(..., description="6位股票代码")):
    """主力资金概况"""
    return get_stock_spot(symbol)
