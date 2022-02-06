import json
import numpy as np
import argparse
import heapq
from tqdm import tqdm
import os
from tqdm.contrib.concurrent import process_map  # or thread_map

from binance import Client
import time
import matplotlib.pyplot as plt

from TradingBot import MartingaleBotTrailing


def get_api_key(file_path):
    with open(file_path, 'r') as infile:
        k = json.load(infile)
        return k['api_key'], k['secret_key']


def time_stamp_to_string(time_stamp):
    struct_time = time.localtime(time_stamp)  # 轉成時間元組
    return time.strftime("%Y-%m-%d %H:%M:%S", struct_time)  # 轉成字串


def create_params():
    params = []
    for mbt in [7, 8, 9]:
        for nbr in [1.5, 1.6, 1.7, 1.8]:
            for b0 in [1.5, 1.6, 1.7, 1.8]:
                for b1 in [0.4, 0.5, 0.6]:
                    for s0 in [1.1, 1.2, 1.3, 1.4]:
                        for s1 in [0.1, 0.2, 0.3]:
                            params.append((mbt, nbr, b0, b1, s0, s1))
    return params


def test_bot(param_and_klines):
    (mbt, nbr, b0, b1, s0, s1), klines = param_and_klines
    m_bot = MartingaleBotTrailing(100.0,
                                  max_buy_time=mbt,
                                  next_buy_rate=nbr,
                                  start_buy_after_down_rate=b0,
                                  buy_after_up_rate=b1,
                                  start_sell_rate=s0,
                                  sell_after_down_rate=s1)
    m_label = "b0: {}, b1: {}, s0: {}, s1: {}, n: {}, mbt: {}".format(
        m_bot.start_buy_after_down_rate, m_bot.buy_after_up_rate,
        m_bot.start_sell_rate, m_bot.sell_after_down_rate, m_bot.next_buy_rate,
        m_bot.max_buy_time)
    y_vals = []
    for i, k in enumerate(klines):
        open_time, op, hi, lo, cl, vol, close_time, _, _, _, _, _ = k

        op = float(op)
        hi = float(hi)
        lo = float(lo)
        cl = float(cl)

        price_order = []
        if (op < cl):
            price_order = [op, lo, hi, cl]
        else:
            price_order = [op, hi, lo, cl]

        # price_order = [op, cl]
        # print(time_stamp_to_string(open_time/1000), op, cl)
        for price in price_order:
            r = m_bot.parse_current_status(price)
            y_vals.append(r)
    if (min(y_vals) < -10):
        return (-100, None, None)

    max_count = 500

    return (y_vals[-1], y_vals[::len(y_vals) // max_count], m_label)


def run_coin_test(coin_id, test_days, client):
    plot_title = str(test_days) + " day ago UTC"
    klines = client.get_historical_klines(coin_id + "USDT",
                                          Client.KLINE_INTERVAL_1MINUTE,
                                          plot_title)

    start_time_string = "2022-01-22 09:23:41"
    struct_time = time.strptime(start_time_string, "%Y-%m-%d %H:%M:%S")
    start_time_stamp = int(time.mktime(struct_time) * 1000)

    x = []
    params = create_params()
    top_10 = []

    params_and_klines = [(param, klines) for param in params]
    results = process_map(test_bot,
                          params_and_klines,
                          max_workers=16,
                          chunksize=4)

    for result in results:
        if (len(top_10) >= 15):
            heapq.heappushpop(top_10, result)
        else:
            heapq.heappush(top_10, result)

    fig, ax = plt.subplots(figsize=(12, 8))
    x = [test_days * i / len(top_10[0][1]) for i in range(len(top_10[0][1]))]
    best_y = 0.0
    while (top_10):
        _, y, l = heapq.heappop(top_10)
        ax.plot(x, y, label=l)
        best_y = y[-1]
    print("best:", best_y)

    ax.set(xlabel='time (s)',
           ylabel='profit rate',
           title=coin_id + " from " + plot_title)
    ax.hlines([best_y],
              0,
              1,
              transform=ax.get_yaxis_transform(),
              colors='r',
              label="best profit rate: {0:.4f}%".format(best_y))
    ax.grid()
    ax.legend()
    if (not os.path.exists("results")):
        os.makedirs("results")
    plt.savefig("results/Days{0:03d}_{1}_USDT_days.png".format(
        test_days, coin_id))
    plt.close()


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-k",
                        "--key_json",
                        help="api key json file path",
                        dest='file_path',
                        required=True)
    args = parser.parse_args()
    file_path = args.file_path
    api_key, api_secret = get_api_key(file_path)

    client = Client(api_key, api_secret)

    # fetch 1 minute klines for the last day up until now
    test_day_set = [60]
    # coin_ids = ["MATIC", "FTT", "XLM", "DOT", "SOL", "CRV", "UNI", "BTC", "ETH"]
    coin_ids = ["SHIB"]
    for test_days in test_day_set:
        for coin_id in coin_ids:
            print(coin_id)
            run_coin_test(coin_id, test_days, client)
    exit()


if __name__ == '__main__':
    main()