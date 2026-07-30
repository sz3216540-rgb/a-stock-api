from fastapi import FastAPI
import akshare as ak
import uvicorn

app = FastAPI(title="A股数据接口服务")

# 技能 1：获取股票实时行情与估值
@app.get("/stock_spot")
def get_stock_spot(symbol: str):
    """根据 6 位股票代码（如 600519）获取实时行情与估值"""
    try:
        df = ak.stock_zh_a_spot_em()
        res = df[df["代码"] == symbol]
        if not res.empty:
            return res.to_dict(orient="records")[0]
        return {"error": "未找到相关股票"}
    except Exception as e:
        return {"error": str(e)}

# 技能 2：获取最新财务数据
@app.get("/stock_financial")
def get_stock_financial(symbol: str):
    """获取最新季度/年度的主要财务指标"""
    try:
        df = ak.stock_financial_abstract_THS(symbol=symbol, indicator="按报告期")
        return df.head(4).to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}

# 技能 3：获取资金流向数据
@app.get("/stock_money_flow")
def get_stock_money_flow(symbol: str):
    """获取主力资金流向"""
    try:
        market = "sh" if symbol.startswith("6") else "sz"
        df = ak.stock_individual_fund_flow(stock=symbol, market=market)
        return df.head(5).to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # 启动服务，监听 8000 端口
    uvicorn.run(app, host="0.0.0.0", port=8000)