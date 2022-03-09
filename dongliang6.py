import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels import regression
import matplotlib.pyplot as plt
import requests
import re
import bs4
import akshare as ak
import pickle
import numpy as np
from datetime import datetime
from datetime import date

def save_obj(obj, name):
    with open(name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


def load_obj(name):
    with open(name + '.pkl', 'rb') as f:
        return pickle.load(f)

import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels import regression
import matplotlib.pyplot as plt
import requests
import re
import bs4
import akshare as ak

def cal_rsrs(data2, data1, N=16):
    """
    计算data2中标的所在日期的RSRS斜率指标和拟合优度
    """
    data11 = data1[data1['sec_code'].isin(data2['sec_code'])].reset_index()
    loc = data11[data11['tradeday'].isin(data2['tradeday'])].index.tolist()
    if loc[0] >= N:
        x = sm.add_constant(data11['low_slice'][(loc[0] - N):loc[0]]).astype('float64')
        y = data11['high_slice'][(loc[0] - N):loc[0]].astype('float64')
        est = sm.OLS(y, x)
        res = est.fit()
        params = res.params.low_slice
        r_squared = res.rsquared
    else:
        params = None
        r_squared = None
    data2['rsrs'] = params
    data2['r_squared'] = r_squared
    return data2


def rsrs(data, N=16):
    """
    由日频数据计算RSRS斜率指标和拟合优度
    """
    data = data.dropna()
    data['tradeday'] = pd.to_datetime(data['tradeday'], format='%Y/%m/%d %H:%M:%S')
    data.sort_values(by=['sec_code', 'tradeday'], inplace=True)
    data1 = data.copy()
    data1 = data1.groupby(['sec_code', 'tradeday']).apply(lambda x, data1=data1, N=N: cal_rsrs(x, data1, N))
    print("RSRS斜率指标和拟合优度已计算")

    return data1


def cal_rsrs_std(data2, data1, M=300, N=16):
    """
    计算data2中标的所在日期的RSRS标准分
    """
    data11 = data1[data1['sec_code'].isin(data2['sec_code'])].reset_index()
    loc = data11[data11['tradeday'].isin(data2['tradeday'])].index.tolist()
    # print(loc[0])
    rsrs = data2['rsrs']
    if loc[0] < M + N:
        rsrs_std = None
    else:
        rsrs_mean = np.mean(data11['rsrs'][(loc[0] - M):loc[0]])
        rsrs_s = np.std(data11['rsrs'][(loc[0] - M):loc[0]])
        rsrs_std = (rsrs - rsrs_mean) / rsrs_s
    data2['rsrs_std'] = rsrs_std
    return data2


def rsrs_std(data1, M=300, N=16):
    """
    由RSRS斜率计算RSRS标准分
    """
    data2 = data1.groupby(['sec_code', 'tradeday']).apply(lambda x, data1=data1, M=M, N=N: cal_rsrs_std(x, data1, M, N))
    print("RSRS标准分已计算")
    return data2


def rsrs_std_cor(data2):
    """
    由RSRS标准分计算RSRS修正标准分
    """
    data2['rsrs_std_cor'] = data2['r_squared'] * data2['rsrs_std']
    print('RSRS修正标准分已计算')
    return data2


def rsrs_std_cor_right(data2):
    """
    由RSRS修正标准分计算RSRS右偏修正标准分
    """
    data2['rsrs_std_cor_right'] = data2['rsrs_std_cor'] * data2['rsrs']
    print('RSRS右偏修正标准分已计算')
    return data2


def rsrs_std_cor_right_mean(data2, ndays=5):
    """
    计算RSRS右偏修正标准分的ndays均线
    """
    data2['rsrs_std_cor_right_mean']=data2.groupby('sec_code')['rsrs_std_cor_right'].rolling(window=ndays).mean()

    # data2['rsrs_std_cor_right_mean'] = data2.groupby('sec_code')['rsrs_std_cor_right'].apply(pd.rolling_mean, ndays)
    print('RSRS右偏修正标准分均线已计算')
    return data2


def get_rsrs(data, N=16, M=300, ndays=5):
    """
    根据日频数据计算RSRS相关指标
    data 数据，包括：标的代码sec_code,交易日tradeday,最高价high_slice、最低价low_slice、收盘价close_slice
    N，回归时间窗口，默认取16，不足16赋值为None
    M，标准分计算窗口，默认取300，不足300赋值为None
    """
    data1 = rsrs(data, N)
    data2 = rsrs_std(data1, M, N)
    data2 = rsrs_std_cor(data2)
    data2 = rsrs_std_cor_right(data2)
    data2 = rsrs_std_cor_right_mean(data2, ndays)
    return data2


def get_signal(data2, S):
    """
    根据RSRS指标和阈值S判断是否有交易信号（最简单的情况）,trade_dir为0代表买入，为1代表卖出，为-1代表无信号
    """
    data3 = data2.copy()
    data3.loc[:,'trade_dir']=-1
    data3.loc[(data3['rsrs_std_cor_right'] > S) & (data3['trade_dir'] == -1), 'trade_dir'] = 0
    data3.loc[(data3['rsrs_std_cor_right'] > S) & (data3['trade_dir'] == 1), 'trade_dir'] = -1

    data3.loc[(data3['rsrs_std_cor_right'] < -S) & (data3['trade_dir'] == -1), 'trade_dir'] = 1
    data3.loc[(data3['rsrs_std_cor_right'] < -S) & (data3['trade_dir'] == 0), 'trade_dir'] = -1
    # data3.drop(['rsrs','r_squared','rsrs_std','rsrs_std_cor','rsrs_std_cor_right'], axis = 1, inplace = True)
    return data3


def RSRS(data, N=16, M=300, S=0.7, ndays=5):
    """
    根据日频数据计算RSRS相关指标，并判断交易信号，更新trade_dir,删除中间变量
    """
    data2 = get_rsrs(data, N, M, ndays)
    data3 = get_signal(data2, S)
    return data3


def single_stock_tradeback(stock_code,etf_kline,money,trade_pay_rate,start_date,end_date):

    '''

    :param stock_code:  str  股票代码，例：'sz159966'
    :param etf_kline:  dict  全部etf基金k线，
    :param money: float  初始买入成本，包含手续费
    :param trade_pay_rate: float，手续费费率，【0-1】
    :param start_date: date   回测开始日期，
    :param end_date: date   回测结束日期，
    :return: pandas.Dataframe  包含净值等信息的
    '''
    etf_kline_stock=etf_kline[stock_code]
    etf_hold = etf_kline_stock[start_date:end_date]
    etf_close = etf_hold['close']
    etf_close_shift = etf_close.shift(1)
    etf_delta = (etf_close - etf_close_shift) / etf_close_shift
    etf_delta = etf_delta.drop(start_date)
    etf_hold['incresing_rate'] = etf_delta
    etf_hold.loc[start_date, 'incresing_rate'] = (etf_hold.loc[start_date, 'close'] - etf_hold.loc[
        start_date, 'open']) / etf_hold.loc[start_date, 'open']
    etf_hold['日增长倍数'] = etf_hold['incresing_rate'] + 1
    etf_hold['净值倍数'] = etf_hold['日增长倍数'].cumprod()
    money_after_trade=money* (1 - trade_pay_rate)
    etf_hold['金额'] = etf_hold['净值倍数'] * money_after_trade
    etf_hold.loc[start_date, '手续费'] = money * trade_pay_rate
    etf_hold.loc[end_date, '手续费'] = etf_hold.loc[end_date, '金额'] * trade_pay_rate

    etf_hold.loc[end_date, '卖出金额_手续费后'] = etf_hold.loc[end_date, '金额'] * (1 - trade_pay_rate)
    return etf_hold,etf_hold.loc[end_date, '金额'] * (1 - trade_pay_rate)


def etf_get():
    etf_list = ak.fund_etf_category_sina(symbol="ETF基金")
    res={}
    res1 = {}
    res2 = {}
    res3 = {}
    res4 = {}
    res5 = {}
    n = 1
    for i in etf_list['symbol']:
        if i == 'sh513200' or i == 'sh513150':
            continue
        print(i)
        print(n)
        fund_etf_hist_sina_df = ak.fund_etf_hist_sina(symbol=i)

        fund_etf_hist_sina_df.set_index(['date'], inplace=True)
        # ma12 = fund_em_etf_fund_info_df['单位净值'].rolling(window=5).mean()
        close = fund_etf_hist_sina_df['close']
        open_etf = fund_etf_hist_sina_df['open']
        high = fund_etf_hist_sina_df['high']
        low = fund_etf_hist_sina_df['low']
        volume = fund_etf_hist_sina_df['volume']
        fund_etf_hist_sina_df=pd.to_numeric(fund_etf_hist_sina_df).sort_index()
        close = pd.to_numeric(close).sort_index()
        open_etf = pd.to_numeric(open_etf).sort_index()
        high = pd.to_numeric(high).sort_index()
        low = pd.to_numeric(low).sort_index()
        volume = pd.to_numeric(volume).sort_index()
        fund_etf_hist_sina_df=fund_etf_hist_sina_df.sort_index()

        close = close.sort_index()
        open_etf = open_etf.sort_index()
        high = high.sort_index()
        low = low.sort_index()
        volume = volume.sort_index()
        # jinzi_delta=jinzi.shift(20)
        # mtm_20=(jinzi-jinzi_delta)/jinzi
        res[i]=fund_etf_hist_sina_df
        res1[i] = close
        res2[i] = open_etf
        res3[i] = high
        res4[i] = low
        res5[i] = volume
        n = n + 1
    save_obj(res, 'etf_all')
    # save_obj(res1, 'etf_close')
    # save_obj(res2, 'etf_open')
    # save_obj(res3, 'etf_high')
    # save_obj(res4, 'etf_low')
    # save_obj(res5, 'etf_volume')

def date_mtm():
    money=1

    trade_pay_rate=0.1#0.00015

    money_after_trade=money*(1-trade_pay_rate)

    etf_kline=ak.fund_etf_hist_sina('sz159966')
    etf_kline.set_index(etf_kline['date'],inplace=True)
    start_date=date(2019,12,27)
    end_date=date(2020,1,6)

    etf_close = load_obj('etf_close')
    etf_all = pd.concat(etf_close, axis=1)
    etf_all = etf_all.sort_index()

    delta_etf_all = etf_all.shift(6)
    mtm_20 = (etf_all - delta_etf_all) / etf_all
    mtm_20['stock_mtm_max'] = mtm_20.idxmax(axis=1)

    mtm_20['stock_hold'] = mtm_20['stock_mtm_max'].shift(1)
    mtm_20 = mtm_20.dropna(how='all')
    mtm_20['test']=mtm_20.loc[mtm_20['stock_hold']=='sz159902','sz159902']


    for i in mtm_20.iterrows():
        if mtm_20.loc[i[0], 'stock_mtm_max'] != mtm_20.loc[i[0], 'stock_hold']:
            mtm_20.loc[i[0], 'hold_change'] = 1
        elif mtm_20.loc[i[0], 'stock_mtm_max'] == mtm_20.loc[i[0], 'stock_hold']:
            mtm_20.loc[i[0], 'hold_change'] = 0
        try:

            mtm_20.loc[i[0], 'sell_price'] = etf_close[i[1]['stock_hold']][i[0]]
        except:
            pass

    mtm_20=mtm_20[mtm_20['sell_price'].notnull()]

    res=[]
    res2=[]
    res3={}
    for i in zip(mtm_20.index,mtm_20['stock_mtm_max'],mtm_20['stock_hold']):
        if i[1]==i[2]:

            res.append(i[0])
        elif i[1]!=i[2]:
            res.append(i[0])
            res2.append(res)
            res.append(i[2])
            # res3[i[2]]=res
            res=[]
    return res2


if __name__=='__main__':

    res2=date_mtm()
    etf_all=load_obj('etf_all')
    res=[]
    qian=[]
    quxian=1
    aaa=pd.DataFrame()
    fuck=[]
    for i in res2:
        stock=i[-1]
        date_range=i[0:-1]
        start=min(date_range)
        end=max(date_range)
        if start>date(2018,1,17) and end<date(2018,1,25):
            fuck.append(i)
            # etf_kline=etf_all[stock]
            test1,test2=single_stock_tradeback(stock, etf_all, 1, 0.0001, start, end)
            jinzi,quxian=single_stock_tradeback(stock,etf_all,quxian,0,start,end)
            aa=jinzi['金额']
            qian.append(aa)
            res.append(quxian)
    aaa=pd.concat(qian)
    plt.plot(aaa)

    plt.show()

    n=1
    buy_date= {}
    for i in res2:
        buy_date[i[0]]=n
        n=n+1
        if len(i)>2:
            for ii in i[1:-1]:
                buy_date[ii] = 0
    zzz = pd.DataFrame.from_dict([buy_date]).T


    #
    #
    # stock_zh_index_daily_df = ak.stock_zh_index_daily(symbol="sh000300")
    # stock_zh_index_daily_df['tradeday']=stock_zh_index_daily_df.index
    # stock_zh_index_daily_df['high_slice']=stock_zh_index_daily_df['high']
    # stock_zh_index_daily_df['low_slice'] = stock_zh_index_daily_df['low']
    # stock_zh_index_daily_df['close_slice'] = stock_zh_index_daily_df['close']
    # stock_zh_index_daily_df['sec_code'] = 'sz399552'
    # rsrs_=RSRS(stock_zh_index_daily_df, N=16, M=300, S=0.7, ndays=5)
    # data2 = get_rsrs(stock_zh_index_daily_df, N=16, M=300,  ndays=5)
    # data2.loc[:,'trade_dir']=-1
    # S=0.7
    # data2.loc[(data2['rsrs_std_cor_right'] > S) & (data2['trade_dir'] == -1), 'trade_dir'] = 0
    #
    # date_rsrs=data2[data2['rsrs_std_cor_right']>S]
    #
    #
    # res3=[]
    # for i in res2:
    #     res4=[]
    #     for ii in i:
    #         if ii in list(date_rsrs.index):
    #             res4.append(ii)
    #     if res4!=[]:
    #         res4.append(i[-1])
    #         res3.append(res4)
    #
    #
    # res2=res3
    # etf_all=load_obj('etf_all')
    # res=[]
    # qian=[]
    # quxian=1
    # aaa=pd.DataFrame()
    # for i in res2:
    #     stock=i[-1]
    #     date_range=i[0:-1]
    #     start=min(date_range)
    #     end=max(date_range)
    #     if start>date(2012,12,1):
    #         # etf_kline=etf_all[stock]
    #         test1,test2=single_stock_tradeback(stock, etf_all, 1, 0.0001, start, end)
    #         jinzi,quxian=single_stock_tradeback(stock,etf_all,quxian,0,start,end)
    #         aa=jinzi['金额']
    #         qian.append(aa)
    #         res.append(quxian)
    # aaa=pd.concat(qian)
    # plt.plot(aaa)
    #
    # plt.show()
    #
    # n=1
    # buy_date= {}
    # for i in res2:
    #     buy_date[i[0]]=n
    #     n=n+1
    #     if len(i)>2:
    #         for ii in i[1:-1]:
    #             buy_date[ii] = 0
    # zzz = pd.DataFrame.from_dict([buy_date]).T