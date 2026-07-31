from fastapi import FastAPI, Query
import requests

app = FastAPI(title="A股数据 API 服务")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

@app.get("/stock_spot")
def get_stock_spot(symbol: str = Query(..., description="6位股票代码")):
    """获取股票实时行情（腾讯财经防封接口）"""
    try:
        prefix = "sh" if symbol.startswith("6") or symbol.startswith("9") else "sz"
        url = f"http://qt.gtimg.cn/q={prefix}{symbol}"
        
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.encoding = 'gbk' # 腾讯接口使用 GBK 编码
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
    count: int = Query(30, description="需要获取的历史交易日天数，例如：30, 60, 100")
):
    """获取股票历史日线数据（支持查询任意历史天数及每日涨跌幅）"""
    try:
        prefix = "sh" if symbol.startswith("6") or symbol.startswith("9") else "sz"
        # 这里的 count 参数可以让接口动态请求指定天数的数据
        url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={prefix}{symbol},day,,,{count},qfq"
        res = requests.get(url, headers=HEADERS, timeout=10)
        data = res.json()
        
        # 解析腾讯返回的 K 线数组
        stock_data = data["data"][f"{prefix}{symbol}"]
        day_klines = stock_data.get("day", [])
        
        history_list = []
        prev_close = None  # 用于计算涨跌幅的前一日收盘价
        
        for item in day_klines:
            # item 格式: [日期, 开盘价, 收盘价, 最高价, 最低价, 成交量]
            open_price = float(item[1])
            close_price = float(item[2])
            high_price = float(item[3])
            low_price = float(item[4])
            volume = float(item[5])
            
            # 计算当日涨跌幅
            pct_change = 0.0
            if prev_close and prev_close > 0:
                pct_change = round(((close_price - prev_close) / prev_close) * 100, 2)
            prev_close = close_price  # 更新前一日收盘价
            
            history_list.append({
                "日期": item[0],
                "开盘价": open_price,
                "收盘价": close_price,
                "最高价": high_price,
                "最低价": low_price,
                "成交量(手)": volume,
                "涨跌幅(%)": pct_change
            })
            
        return {"status": "success", "symbol": symbol, "count": len(history_list), "data": history_list}
    except Exception as e:
        return {"status": "error", "message": f"历史行情获取失败: {str(e)}"}
@app.get("/stock_financial")
def get_stock_financial(symbol: str = Query(..., description="6位股票代码")):
    """简易财务概况"""
    return get_stock_spot(symbol)

@app.get("/stock_money_flow")
def get_stock_money_flow(symbol: str = Query(..., description="6位股票代码")):
    """主力资金概况"""
    return get_stock_spot(symbol)
