import json
import numpy as np
import argparse
from binance import Client, ThreadedWebsocketManager, ThreadedDepthCacheManager


def get_api_key(file_path):
    with open(file_path, 'r') as infile:
        k = json.load(infile)
        return k['api_key'], k['secret_key']


class MartingaleBot():

    trade_fee_rate = 0.0005

    def __init__(self,
                 init_usdt,
                 max_buy_time=8,
                 next_buy_rate=1.8,
                 start_buy_after_down_rate=1.5,
                 buy_after_up_rate=0.4,
                 start_sell_rate=0.8,
                 sell_after_down_rate=0.2) -> None:

        self.init_usdt = init_usdt
        self.total_usdt_val = init_usdt
        self.max_buy_time = max_buy_time
        self.next_buy_rate = next_buy_rate
        self.start_buy_after_down_rate = start_buy_after_down_rate
        self.buy_after_up_rate = buy_after_up_rate
        self.start_sell_rate = start_sell_rate
        self.sell_after_down_rate = sell_after_down_rate

        # start
        self.start_new_round()

    def start_new_round(self):

        print("current usdt:", self.total_usdt_val)
        # calulate first step
        t = 1
        for i in range(self.max_buy_time):
            t += self.next_buy_rate**i
        step = self.total_usdt_val / t

        # seperate usdt into incremental steps
        self.sep_usdt = [step]
        for i in range(self.max_buy_time):
            self.sep_usdt.append(step * (self.next_buy_rate**i))

        # print(self.sep_usdt)
        # print(sum(self.sep_usdt))

        # set init coin
        self.total_coin_amount = 0.0
        self.coin_avg_usdt = 0
        self.start_track_buy_price = None
        self.current_lowest_price = None
        self.start_track_sell_price = None
        self.current_highest_price = None
        self.track_buying = False
        self.track_selling = False
        self.first_trade = True

    def buy_coin(self, coin_price, usdt):
        trade_fee = usdt * MartingaleBot.trade_fee_rate
        buy_amount = (usdt - trade_fee) / coin_price

        self.coin_avg_usdt = (self.total_coin_amount * self.coin_avg_usdt +
                              buy_amount * coin_price) / (
                                  self.total_coin_amount + buy_amount)
        self.total_coin_amount += buy_amount

        self.start_track_buy_price = coin_price * (
            1.0 - self.start_buy_after_down_rate / 100.0)

        self.start_track_sell_price = self.coin_avg_usdt * (
            1.0 + self.start_sell_rate / 100.0) / (
                1.0 - MartingaleBot.trade_fee_rate)

        print("buy amount:", buy_amount)
        print("buy price:", coin_price)
        print("start_track_buy_price:", self.start_track_buy_price)
        print("start_track_sell_price:", self.start_track_sell_price)

        self.track_buying = False

    def sell_coin(self, coin_price):
        get_usdt = self.total_coin_amount * coin_price
        trade_fee = get_usdt * MartingaleBot.trade_fee_rate

        self.total_usdt_val = get_usdt - trade_fee + sum(self.sep_usdt)
        print("### sell ###")
        self.start_new_round()
        self.track_selling = False

    def change_status(self, price):
        if(self.sep_usdt and price <= self.start_track_buy_price):
            print("---start track buying---")
            self.track_buying = True
            self.current_lowest_price = price
        elif(price >= self.start_track_sell_price):
            print("---start track selling---")
            self.track_selling = True
            self.current_highest_price = price

    def parse_current_status(self, price):

        if (self.first_trade):
            usdt = self.sep_usdt.pop(0)
            self.buy_coin(price, usdt)
            self.current_lowest_price = price
            self.current_highest_price = price
            self.first_trade = False
        elif (self.track_buying):
            buy_threshold = self.current_lowest_price*(1.0+self.buy_after_up_rate/100.0)
            # print(buy_threshold)
            if(price >= buy_threshold):
                usdt = self.sep_usdt.pop(0)
                self.buy_coin(buy_threshold, usdt)
            else:
                self.current_lowest_price = min(price, self.current_lowest_price)
        elif (self.track_selling):
            sell_threshold = self.current_highest_price*(1.0-self.sell_after_down_rate/100.0)
            if(price <= sell_threshold):
                self.sell_coin(sell_threshold)
            else:
                self.current_highest_price = max(price, self.current_highest_price)
        else:
            self.change_status(price)

    def print_status(self):
        print(self.total_coin_amount)
        print(self.coin_avg_usdt)


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
    klines = client.get_historical_klines("XLMUSDT",
                                          Client.KLINE_INTERVAL_1MINUTE,
                                          "1 day ago UTC")

    init_val = 75.7 + 2.5706
    m_bot = MartingaleBot(init_val)
    a = 0.195338
    b = 0.189
    c = 0.197
    d = 0.195
    price_list = np.linspace(a,b,20, False).tolist() + np.linspace(b, c, 20, False).tolist() + np.linspace(c, d, 20, False).tolist()
    for p in price_list:
        m_bot.parse_current_status(p)

    exit()
    # print(b/a)

    for i, k in enumerate(klines):
        # print(k)
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

        for price in price_order:
            m_bot.parse_current_status(price)
            # m_bot.print_status()
        break

    exit()


if __name__ == '__main__':
    main()