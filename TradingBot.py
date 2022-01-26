class MartingaleBotTrailing():

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
        self.record_round = 0
        self.record_sell = []
        self.show_debug = False

        # start
        self.start_new_round()

    def start_new_round(self):

        if(self.show_debug):
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
        trade_fee = usdt * MartingaleBotTrailing.trade_fee_rate
        buy_amount = (usdt - trade_fee) / coin_price

        self.coin_avg_usdt = (self.total_coin_amount * self.coin_avg_usdt +
                              buy_amount * coin_price) / (
                                  self.total_coin_amount + buy_amount)
        self.total_coin_amount += buy_amount

        self.start_track_buy_price = coin_price * (
            1.0 - self.start_buy_after_down_rate / 100.0)

        self.start_track_sell_price = self.coin_avg_usdt * (
            1.0 + self.start_sell_rate / 100.0) / (
                1.0 - MartingaleBotTrailing.trade_fee_rate)

        if(self.show_debug):
            print("  buy amount:", buy_amount)
            print("  buy price:", coin_price)
            print("  start_track_buy_price:", self.start_track_buy_price)
            print("  start_track_sell_price:", self.start_track_sell_price)

        self.track_buying = False

    def sell_coin(self, coin_price):
        get_usdt = self.total_coin_amount * coin_price
        trade_fee = get_usdt * MartingaleBotTrailing.trade_fee_rate
        profit = get_usdt - trade_fee
        self.total_usdt_val = profit + sum(self.sep_usdt)
        self.record_sell.append((self.max_buy_time-len(self.sep_usdt), (self.total_usdt_val-self.init_usdt)/self.init_usdt*100))

        if(self.show_debug):
            print("### sell ###")
        self.record_round += 1
        self.start_new_round()
        self.track_selling = False

    def change_status(self, price):
        if (self.sep_usdt and price <= self.start_track_buy_price):

            if(self.show_debug):
                print("---start track buying---")
            self.track_buying = True
            self.current_lowest_price = price
        elif (price >= self.start_track_sell_price):
            if(self.show_debug):
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
            buy_threshold = self.current_lowest_price * (
                1.0 + self.buy_after_up_rate / 100.0)
            # print(buy_threshold)
            if (price >= buy_threshold):
                usdt = self.sep_usdt.pop(0)
                self.buy_coin(buy_threshold, usdt)
            else:
                self.current_lowest_price = min(price,
                                                self.current_lowest_price)
        elif (self.track_selling):
            sell_threshold = self.current_highest_price * (
                1.0 - self.sell_after_down_rate / 100.0)
            if (price <= sell_threshold):
                self.sell_coin(sell_threshold)
            else:
                self.current_highest_price = max(price,
                                                 self.current_highest_price)
        else:
            self.change_status(price)
        return ((self.total_coin_amount*price+sum(self.sep_usdt))/self.init_usdt-1)*100

    def print_status(self):
        print("#### STATUS ####")
        print("  finish round:", self.record_round)
        print("  profit:", (self.total_usdt_val - self.init_usdt))
        print("  earning rate:{0:.3f}%".format((self.total_usdt_val-self.init_usdt)/self.init_usdt*100) )
