import json
import numpy as np
import argparse
import heapq
from tqdm import tqdm
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
        for nbr in [1.6, 1.7, 1.8]:
            for b0 in [1.6, 1.7, 1.8]:
                for b1 in [0.4, 0.5, 0.6]:
                    for s0 in [0.7, 0.8, 0.9, 1.0]:
                        for s1 in [0.1, 0.2, 0.3]:
                            params.append((mbt, nbr, b0, b1, s0, s1))
    return params

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
    plot_title = "90 day ago UTC"
    klines = client.get_historical_klines("XLMUSDT",
                                          Client.KLINE_INTERVAL_1MINUTE,
                                          plot_title)
    print("Get klines")

    init_val = 75.7
    start_time_string = "2022-01-22 09:23:41"
    struct_time = time.strptime(start_time_string, "%Y-%m-%d %H:%M:%S")
    start_time_stamp = int(time.mktime(struct_time) * 1000)

    # end_time_string = "2022-01-23 09:22:41"
    # struct_time = time.strptime(end_time_string, "%Y-%m-%d %H:%M:%S")
    # end_time_stamp = int(time.mktime(struct_time)*1000)
    # print(len(params))
    # exit()

    x = []
    params = create_params()
    top_10 = []


    for mbt, nbr, b0, b1, s0, s1 in tqdm(params):
        m_bot = MartingaleBotTrailing(init_val,
                                max_buy_time=mbt,
                                next_buy_rate=nbr,
                                start_buy_after_down_rate=b0,
                                buy_after_up_rate=b1,
                                start_sell_rate=s0,
                                sell_after_down_rate=s1)
        m_label = "b0: {},b1: {}, s0: {}, s1: {}, n: {}, mbt: {}".format(
            m_bot.start_buy_after_down_rate, m_bot.buy_after_up_rate,
            m_bot.start_sell_rate, m_bot.sell_after_down_rate, m_bot.next_buy_rate, m_bot.max_buy_time)
        y_vals = []
        for i, k in enumerate(klines):
            # print(k)
            open_time, op, hi, lo, cl, vol, close_time, _, _, _, _, _ = k
            # if(open_time < start_time_stamp):
            #     continue

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
        if(min(y_vals) < -5):
            continue
        elif(len(top_10) >= 10):
            heapq.heappushpop(top_10, (y_vals[-1], y_vals, m_label))
        else:
            heapq.heappush(top_10, (y_vals[-1], y_vals, m_label))
    # m_bot.print_status()
    # x = []
    # y = []
    # for i, p in enumerate(m_bot.record_sell):
    #     x.append(i)
    #     y.append(p[1])

    fig, ax = plt.subplots()
    x = [i for i in range(len(top_10[0][1]))]
    while(top_10):
        _, y, l = heapq.heappop(top_10)
        ax.plot(x, y, label=l)

    ax.set(xlabel='time (s)', ylabel='profit rate', title=plot_title)
    ax.grid()
    ax.legend()

    plt.show()
    exit()


if __name__ == '__main__':
    main()