import asyncio
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
import akshare as ak
import pandas as pd

app = FastAPI(title="A股数据 API 服务 (AkShare 版)")

def clean_symbol(symbol: str) -> str:
    """提取 6 位数字股票代码"""
    code = "".join(filter(str.isdigit, symbol))
    if len(code) != 6:
        raise ValueError("股票代码格式不正确，请输入6位数字代码")
    return code

def clean_dataframe(df: pd.DataFrame):
    """清理 DataFrame 中的 NaN / Inf，方便 FastAPI 转为 JSON 输出"""
    if df is None or df.empty:
        return []
    # 将 NaN、Inf 替换为 None，便于 JSON 序列化
    df = df.where(pd.notnull(df), None)
    return df.to_dict(orient="records")

@app.get("/stock_spot")
async def get_stock_spot(symbol: str = Query(..., description="6位股票代码，如 002891 或 002891.SZ")):
    """获取股票实时行情（基于 AkShare 东方财富源）"""
    try:
        code = clean_symbol(symbol)
        
        # AkShare 的请求是同步阻塞的，放到 asyncio.to_thread 里运行，配合 wait_for 设置 8 秒超时
        # stock_zh_a_spot_em 返回全量或指定股票的实时盘口
        spot_df = await asyncio.wait_for(
            asyncio.to_thread(ak.stock_zh_a_spot_em), 
            timeout=8.0
        )
        
        # 筛选指定股票
        stock_data = spot_df[spot_df["代码"] == code]
        if stock_data.empty:
            return {"status": "error", "message": f"未查询到股票 {symbol} 的实时行情"}
        
        records = clean_dataframe(stock_data)
        return {
            "status": "success",
            "symbol": symbol,
            "data": records[0]
        }
    except asyncio.TimeoutError:
        return {"status": "error", "message": "请求数据源超时，海外服务器网络波动，请稍后重试"}
    except Exception as e:
        return {"status": "error", "message": f"获取失败: {str(e)}"}

@app.get("/stock_history")
async def get_stock_history(
    symbol: str = Query(..., description="6位股票代码"),
    count: int = Query(30, description="获取的历史天数")
):
    """获取股票历史日线 K 线数据"""
    try:
        code = clean_symbol(symbol)
        
        # 调用 AkShare 日线接口
        df = await asyncio.wait_for(
            asyncio.to_thread(
                ak.stock_zh_a_hist,
                symbol=code,
                period="daily",
                adjust="qfq"
            ),
            timeout=8.0
        )
        
        if df.empty:
            return {"status": "error", "message": f"未查询到股票 {symbol} 的历史行情"}
        
        # 取最近 count 天
        df_recent = df.tail(count)
        return {
            "status": "success",
            "symbol": symbol,
            "count": len(df_recent),
            "data": clean_dataframe(df_recent)
        }
    except asyncio.TimeoutError:
        return {"status": "error", "message": "请求历史行情超时"}
    except Exception as e:
        return {"status": "error", "message": f"历史行情获取失败: {str(e)}"}

@app.get("/stock_financial")
async def get_stock_financial(symbol: str = Query(..., description="6位股票代码")):
    """【财务数据】获取主要财务指标摘要（同花顺/东方财富数据源）"""
    try:
        code = clean_symbol(symbol)
        
        # AkShare 财务指标摘要接口
        df = await asyncio.wait_for(
            asyncio.to_thread(
                ak.stock_financial_abstract_ths,
                symbol=code,
                indicator="按报告期"
            ),
            timeout=10.0
        )
        
        if df.empty:
            return {"status": "error", "message": f"未查询到股票 {symbol} 的财务报表数据"}
            
        return {
            "status": "success",
            "symbol": symbol,
            "data": clean_dataframe(df)
        }
    except asyncio.TimeoutError:
        return {"status": "error", "message": "请求财务数据超时，Render海外节点访问受限，请重试"}
    except Exception as e:
        return {"status": "error", "message": f"财务数据获取失败: {str(e)}"}

@app.get("/stock_money_flow")
async def get_stock_money_flow(symbol: str = Query(..., description="6位股票代码")):
    """【资金流向】获取个股资金流向（主力/大单/散户）"""
    try:
        code = clean_symbol(symbol)
        
        df = await asyncio.wait_for(
            asyncio.to_thread(
                ak.stock_individual_fund_flow,
                stock=code,
                market="sh" if code.startswith("6") or code.startswith("9") else "sz"
            ),
            timeout=8.0
        )
        
        if df.empty:
            return {"status": "error", "message": f"未查询到股票 {symbol} 的资金流向数据"}
            
        return {
            "status": "success",
            "symbol": symbol,
            "data": clean_dataframe(df.tail(15))  # 返回最近15天的资金流向
        }
    except asyncio.TimeoutError:
        return {"status": "error", "message": "获取资金流向超时"}
    except Exception as e:
        return {"status": "error", "message": f"资金流向获取失败: {str(e)}"}
