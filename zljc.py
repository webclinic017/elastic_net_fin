# -*- coding: utf-8 -*-
import datetime
import time
import numpy as np
from sqlalchemy.sql import func
import pandas as pd
import math
from pandas import DataFrame
import akshare as ak
import scipy
import talib
import matplotlib.pyplot as plt
from scipy import stats
from chinese_calendar import is_workday
import chinese_calendar


# def SMA(vals, n, m) :
#     # 算法1
#     return (lambda x, y: ((n - m) * x + y * m) / n, vals)
# code= ak.stock_zh_index_spot
def zhibiao():
    # data=pd.read_csv('天华超净daily.csv',index_col=0)
    data = ak.stock_zh_index_daily_em(symbol='sh000016')
    # data=ak.stock_zh_a_hist(symbol='300390',adjust='hfq')
    data.rename(columns={'open': '开盘', 'high': '最高', 'low': '最低', 'close': '收盘', 'volume': '成交量'}, inplace=True)
    data['日期'] = data.index
    data = data.set_index(['date'])
    data['日期'] = data.index
    var1 = (data['最高'] + data['最低'] + data['收盘']) / 3
    data2 = data.shift(1)

    var2_pre = ((var1 - data2['最低']) - (data['最高'] - var1)) * data['成交量'] / 100000 / (data['最高'] - data['最低'])

    var2_pre = var2_pre.replace([np.inf, -np.inf], np.nan)
    var2_pre = var2_pre.dropna()
    # var2_pre=var2_pre.round(decimals=2)
    date_start = '2005-01-05'
    t = time.strptime(date_start, "%Y-%m-%d")
    y, m, d = t[0:3]
    # df[~df.isin([inf]).any(1)]
    var2 = var2_pre.cumsum(axis='index')
    # res={}
    # var2_0= {}
    # for i in range(1,len(var2_pre)):
    #     # zzz=var2_pre.truncate(after=i,axis="rows")
    #     # zzzz=zzz.drop(i)
    #     zzz=var2_pre[0:i]
    #     res[list(var2_pre.index)[i-1]]=sum(zzz)
    #     a=list(var2_pre.index)[i-1]
    #     var2_0[data['日期'].iloc[a]]=sum(zzz)
    #
    # var2=pd.DataFrame(var2_0,index=[0]).T
    var3 = var2.ewm(span=1, adjust=False).mean()
    jcs = var2.ewm(span=1, adjust=False).mean()
    jcm = var3.rolling(window=12).mean()
    jcl = var3.rolling(window=26).mean()

    lc = data2['收盘']
    data3 = data.set_index(['日期'])
    data2 = data3.shift(1)
    lc = data2['收盘']
    aa = (data3['收盘'] - data2['收盘'])
    aa[aa < 0] = 0
    bb = abs(data3['收盘'] - data2['收盘'])
    # zz=SMA(aa,12,1)
    zzz = {}
    sma_12_1 = aa.ewm(span=2 * 12 / 1 - 1).mean()
    rsi2 = talib.RSI(data3['收盘'], 12)
    rsi3 = talib.RSI(data3['收盘'], 18)
    sma_16_1 = aa.ewm(span=2 * 16 / 1 - 1).mean()
    sma_abs_16_1 = bb.ewm(span=2 * 16 / 1 - 1).mean()
    mms_pre = 3 * rsi2 - 2 * sma_16_1 / sma_abs_16_1 * 100
    mms = talib.MA(mms_pre, 3)
    mmm = talib.EMA(mms, 8)
    sma_12_1 = aa.ewm(span=2 * 12 / 1 - 1).mean()
    sma_abs_12_1 = bb.ewm(span=2 * 12 / 1 - 1).mean()
    mml_pre = 3 * rsi3 - 2 * sma_12_1 / sma_abs_12_1 * 100
    mml = talib.MA(mml_pre, 5)
    return data, jcs, jcm, jcl, mms, mmm, mml


def huiche(data, date_buy, date_sell):
    for i in list(data.index):
        if i in mm_duanxian_buy:
            data.loc[i, '收盘信号'] = 1
        if i in mm_duanxian_sell:
            data.loc[i, '收盘信号'] = 0

    data['当天仓位'] = data['收盘信号'].shift(1)
    data['当天仓位'].fillna(method='ffill', inplace=True)
    data['ret'] = data['收盘'] / data['收盘'].shift(1) - 1
    from datetime import datetime, timedelta

    d = datetime.strptime(data[data['当天仓位'] == 1].index[0], '%Y-%m-%d') - timedelta(days=1)
    d = d.strftime('%Y-%m-%d')
    df_new = data.loc[d:]
    df_new['ret'][0] = 0
    df_new['当天仓位'][0] = 0
    df_new['资金指数'] = (df_new.ret * data['当天仓位'] + 1.0).cumprod()
    df_new['指数净值'] = (df_new.ret + 1.0).cumprod()
    df1 = data[0:]
    df1['策略净值'] = (df1.ret * df1['当天仓位'] + 1.0).cumprod()
    df1['指数净值'] = (df1.ret + 1.0).cumprod()
    df1['策略收益率'] = df1['策略净值'] / df1['策略净值'].shift(1) - 1
    df1['指数收益率'] = df1.ret
    return df1


if __name__ == '__main__':
    data, jcs, jcm, jcl, mms, mmm, mml = zhibiao()
    bias_jc_s_m = ((jcs - jcm) / jcm) * 100
    bias_jc_s_l = ((jcs - jcl) / jcl) * 100
    jcm_delta = jcm.diff()
    jcl_delta = jcl.diff()
    mms_delta = mms.diff()
    mmm_delta = mmm.diff()
    mml_delta = mml.diff()
    data_buy = []
    jc_kongkou = []
    bias_mm_s_l = ((mms - mml) / mml) * 100
    bias_mm_m_l = ((mmm - mml) / mml) * 100
    bias_mm_m_s = (mmm - mms)
    bias_mm_s_m = ((mms - mmm) / mmm) * 100
    for i in jcs.index:
        if jcs[i] < jcm[i] and jcs[i] < jcl[i] and jcm[i] < jcl[i] and jcm_delta[i] < 0 and jcl_delta[i] < 0:
            jc_kongkou.append(i)
    date = list(jcs.index)
    jcs_delta = jcs.diff()
    mm_duanxian_buy = []
    zz = []
    zzz = []
    zzzz = []
    for i in range(2, len(date)):
        if (bias_mm_s_m[date[i - 1]] < bias_mm_s_m[date[i]] and abs(bias_mm_s_m[date[i]]) < 2 and jcm_delta[
            date[i]] > 0 and jcl_delta[date[i]] > 0):
            # if (mms[date[i]] > mmm[date[i]] and mms[date[i - 1]] < mmm[date[i - 1]]) and jcl_delta[date[i]] > 0:
            # mm_duanxian_buy.append(mms.index[i])
            mm_duanxian_buy.append(date[i])
            print(mms.index[i])
            print('fuck', date[i])
            zz.append([date[i], mms_delta[date[i - 4]], mms_delta[date[i - 3]], mms_delta[date[i - 2]],
                       mms_delta[date[i - 1]], mms_delta[date[i]]])
            zzz.append([date[i], bias_mm_s_l[date[i - 2]], bias_mm_s_l[date[i - 1]], bias_mm_s_l[date[i]]])
            zzzz.append([date[i], bias_mm_s_m[date[i - 2]], bias_mm_s_m[date[i - 1]], bias_mm_s_m[date[i]]])
    zz = np.array(zz)
    zzz = np.array(zzz)# -*- coding: utf-8 -*-
import datetime
import time
import numpy as np
from sqlalchemy.sql import func
import pandas as pd
import math
from pandas import DataFrame
import akshare as ak
import scipy
import talib
import matplotlib.pyplot as plt
from scipy import stats
from chinese_calendar import is_workday
import chinese_calendar
# def SMA(vals, n, m) :
#     # 算法1
#     return (lambda x, y: ((n - m) * x + y * m) / n, vals)
# code= ak.stock_zh_index_spot
def zhibiao():
    #data=pd.read_csv('天华超净daily.csv',index_col=0)
    data = ak.stock_zh_index_daily_em(symbol='sh000016')
    # data=ak.stock_zh_a_hist(symbol='300390',adjust='hfq')
    data.rename(columns={'open':'开盘', 'high':'最高', 'low':'最低','close':'收盘','volume':'成交量'}, inplace = True)
    data['日期']=data.index
    data=data.set_index(['date'])
    data['日期']=data.index
    var1=(data['最高']+data['最低']+data['收盘'])/3
    data2=data.shift(1)

    var2_pre=((var1-data2['最低'])-(data['最高']-var1))*data['成交量']/100000/(data['最高']-data['最低'])




    var2_pre=var2_pre.replace([np.inf, -np.inf], np.nan)
    var2_pre=var2_pre.dropna()
    # var2_pre=var2_pre.round(decimals=2)
    date_start='2005-01-05'
    t = time.strptime(date_start, "%Y-%m-%d")
    y, m, d = t[0:3]
    # df[~df.isin([inf]).any(1)]
    var2=var2_pre.cumsum(axis='index')
    # res={}
    # var2_0= {}
    # for i in range(1,len(var2_pre)):
    #     # zzz=var2_pre.truncate(after=i,axis="rows")
    #     # zzzz=zzz.drop(i)
    #     zzz=var2_pre[0:i]
    #     res[list(var2_pre.index)[i-1]]=sum(zzz)
    #     a=list(var2_pre.index)[i-1]
    #     var2_0[data['日期'].iloc[a]]=sum(zzz)
    #
    # var2=pd.DataFrame(var2_0,index=[0]).T
    var3=var2.ewm(span=1,adjust=False).mean()
    jcs=var2.ewm(span=1,adjust=False).mean()
    jcm=var3.rolling(window=12).mean()
    jcl=var3.rolling(window=26).mean()


    lc=data2['收盘']
    data3=data.set_index(['日期'])
    data2=data3.shift(1)
    lc=data2['收盘']
    aa=(data3['收盘']-data2['收盘'])
    aa[aa<0]=0
    bb=abs(data3['收盘']-data2['收盘'])
    # zz=SMA(aa,12,1)
    zzz={}
    sma_12_1=aa.ewm(span=2*12/1-1).mean()
    rsi2=talib.RSI(data3['收盘'],12)
    rsi3=talib.RSI(data3['收盘'],18)
    sma_16_1=aa.ewm(span=2*16/1-1).mean()
    sma_abs_16_1=bb.ewm(span=2*16/1-1).mean()
    mms_pre=3*rsi2-2*sma_16_1/sma_abs_16_1*100
    mms=talib.MA(mms_pre,3)
    mmm=talib.EMA(mms,8)
    sma_12_1=aa.ewm(span=2*12/1-1).mean()
    sma_abs_12_1=bb.ewm(span=2*12/1-1).mean()
    mml_pre=3*rsi3-2*sma_12_1/sma_abs_12_1*100
    mml=talib.MA(mml_pre,5)
    return data,jcs,jcm,jcl,mms,mmm,mml

def huiche(data,date_buy,date_sell):
    for i in list(data.index):
        if i in mm_duanxian_buy:
            data.loc[i, '收盘信号'] = 1
        if i in mm_duanxian_sell:
            data.loc[i, '收盘信号'] = 0

    data['当天仓位'] = data['收盘信号'].shift(1)
    data['当天仓位'].fillna(method='ffill', inplace=True)
    data['ret'] = data['收盘'] / data['收盘'].shift(1) - 1
    from datetime import datetime, timedelta

    d = datetime.strptime(data[data['当天仓位'] == 1].index[0], '%Y-%m-%d') - timedelta(days=1)
    d = d.strftime('%Y-%m-%d')
    df_new = data.loc[d:]
    df_new['ret'][0] = 0
    df_new['当天仓位'][0] = 0
    df_new['资金指数'] = (df_new.ret * data['当天仓位'] + 1.0).cumprod()
    df_new['指数净值'] = (df_new.ret + 1.0).cumprod()
    df1 = data[0:]
    df1['策略净值'] = (df1.ret * df1['当天仓位'] + 1.0).cumprod()
    df1['指数净值'] = (df1.ret + 1.0).cumprod()
    df1['策略收益率'] = df1['策略净值'] / df1['策略净值'].shift(1) - 1
    df1['指数收益率'] = df1.ret
    return df1

if __name__=='__main__':
    data,jcs, jcm, jcl, mms, mmm, mml=zhibiao()
    bias_jc_s_m = ((jcs - jcm) / jcm) * 100
    bias_jc_s_l = ((jcs - jcl) / jcl) * 100
    jcm_delta = jcm.diff()
    jcl_delta = jcl.diff()
    mms_delta=mms.diff()
    mmm_delta=mmm.diff()
    mml_delta=mml.diff()
    data_buy=[]
    jc_kongkou=[]
    bias_mm_s_l=(mms - mml)/ mml * 100
    bias_mm_m_l = ((mmm - mml) / mml) * 100
    bias_mm_m_s=(mmm - mms)
    bias_mm_s_m = ((mms - mmm) / mmm) * 100
    for i in jcs.index:
        if jcs[i]<jcm[i] and jcs[i]<jcl[i] and jcm[i]<jcl[i] and jcm_delta[i]<0 and jcl_delta[i]<0:
            jc_kongkou.append(i)
    date = list(jcs.index)
    jcs_delta=jcs.diff()
    mm_duanxian_buy=[]
    zz=[]
    zzz=[]
    zzzz=[]
    for i in range(2,len(date)):
        #if (jcs[date[i]]>jcm[date[i]]>jcl[date[i]] and jcl_delta[date[i]]>0 and jcm_delta[date[i]]>0) and (mms[date[i]] > mmm[date[i]] and jcl_delta[date[i]]>0 and jcm_delta[date[i]]>0):
        if (mms[date[i]] > mmm[date[i]] and mms[date[i - 1]] < mmm[date[i - 1]]) and jcl_delta[date[i]] > 0 and jcm_delta[date[i]] > 0 :
            #mm_duanxian_buy.append(mms.index[i])
            mm_duanxian_buy.append(date[i])
            print(mms.index[i])
            print('fuck',date[i])
            zz.append([date[i],mms_delta[date[i-4]],mms_delta[date[i-3]],mms_delta[date[i-2]],mms_delta[date[i-1]],mms_delta[date[i]]])
            zzz.append([date[i],bias_mm_s_l[date[i-2]],bias_mm_s_l[date[i-1]],bias_mm_s_l[date[i]]])
            zzzz.append([date[i], bias_mm_s_m[date[i - 2]], bias_mm_s_m[date[i - 1]], bias_mm_s_m[date[i]]])
    zz=np.array(zz)
    zzz=np.array(zzz)

    mm_duanxian_sell=[]
    # mm_duanxian_sell=list(set(list(date))-set(mm_duanxian_buy))
    for i in range(2, len(date)):
        if mms[date[i]] < mmm[date[i]] and mms[date[i - 1]] > mmm[date[i - 1]] and (bias_mm_s_l[date[i-1]]>10 or bias_mm_s_l[date[i]]>10 or bias_mm_s_l[date[i-2]]>10):
        # if (bias_mm_s_l[date[i]]<bias_mm_s_l[date[i-1]]):
            mm_duanxian_sell.append(date[i])
    # for i in jc_kongkou:
    #     mm_duanxian_sell.append(i)

    df=huiche(data,mm_duanxian_sell,mm_duanxian_buy)
    plt.plot(df['策略净值'])
    plt.plot(df['指数净值'])
    plt.show()


    import matplotlib.pyplot as plt

    # plt.plot(data['收盘'])
    data = data[3000:4294]
    data['收盘'].plot(figsize=(16, 7))
    # plt.annotate('买', xy=(np.datetime64(data.index[i]), data['收盘'][i]), arrowprops=dict(facecolor='r', shrink=0.05))
    for i in range(len(data)):
        if data['收盘信号'][i] == 1:
            plt.annotate('买', xy=(i, data['收盘'][i]), arrowprops=dict(facecolor='r', shrink=0.01))
    plt.show()
    data['收盘'].plot(figsize=(16, 7))
    for i in range(len(data)):
        if data['收盘信号'][i] == 0:
            plt.annotate('卖', xy=(i, data['收盘'][i]), arrowprops=dict(facecolor='g', shrink=0.1))
    plt.show()





