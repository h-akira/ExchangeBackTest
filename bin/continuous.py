#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created: 2024-03-09 00:16:51

import sys
import os
import numpy
import pandas as pd
import datetime
from ExchangePackage import chart
from ExchangePackage import check_summer_time
from MyPackage import cprint as print


def time_and_timedelta_calculation(timeObj, timedeltaObj, minus=False):
  if minus:
    return (datetime.datetime.combine(datetime.date(2000,1,1), timeObj) - timedeltaObj).time()
  else:
    return (datetime.datetime.combine(datetime.date(2000,1,1), timeObj) + timedeltaObj).time()

def parse_args():
  import argparse
  parser = argparse.ArgumentParser(description="""\

""", formatter_class = argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("--version", action="version", version='%(prog)s 0.0.1')
  parser.add_argument("-o", "--output", metavar="output-file", default="output", help="output file")
  # parser.add_argument("-", "--", action="store_true", help="")
  # parser.add_argument("file", metavar="input-file", help="input file")
  options = parser.parse_args()
  # if not os.path.isfile(options.file): 
  #   raise Exception("The input file does not exist.") 
  return options

class DataProvider:
  def __init__(self, pair, start_date, end_date, rule=None, DIR=os.path.join(os.path.dirname(__file__), "../data/rate")):
    self.pair = pair
    self.start_date = start_date
    self.end_date = end_date
    self.rule = rule
    self.df_BID = chart.GMO_dir2DataFrame(
      os.path.join(os.path.dirname(__file__), "../data/rate"), 
      pair=pair,
      date_range=[
        start_date,end_date
      ],
      BID_ASK="BID"
    ) 
    self.df_ASK = chart.GMO_dir2DataFrame(
      os.path.join(os.path.dirname(__file__), "../data/rate"),
      pair=pair,
      date_range=[
        start_date,end_date
      ],
      BID_ASK="ASK"
    )
    if len(self.df_BID) != len(self.df_ASK):
      raise Exception("The length of BID and ASK is different.")
    if rule is not None:
      self.df_BID = chart.resample(self.df_BID, rule)
      self.df_ASK = chart.resample(self.df_ASK, rule)
    else:
      self.rule = "1T"
    self.index = self.df_ASK.index
    self.counter = 0
  def get_next(self):
    row_BID = self.df_BID.iloc[self.counter]
    row_ASK = self.df_ASK.iloc[self.counter]
    self.counter += 1
    if self.counter >= len(self.df_BID):
      raise StopIteration
    return {
      "dt": self.index[self.counter].to_pydatetime(),
      "BID":{
        "Open": row_BID["Open"],
        "Close": row_BID["Close"],
        "High": row_BID["High"],
        "Low": row_BID["Low"],
        "Diff": row_BID["Close"] - row_BID["Open"],
      },
      "ASK":{
        "Open": row_ASK["Open"],
        "Close": row_ASK["Close"],
        "High": row_ASK["High"],
        "Low": row_ASK["Low"],
        "Diff": row_ASK["Close"] - row_ASK["Open"],
      }
    }
  def print_info(self):
    print("PAIR:",self.pair)
    print("RULE:",self.rule)
    print("START:",self.start_date)
    print("END:",self.end_date)
    print("BID:")
    print("  開始値:", self.df_BID.iloc[0]["Open"])
    print("  終了値:", self.df_BID.iloc[-1]["Close"])
    print("  終了値ー開始値:", self.df_BID.iloc[-1]["Close"] - self.df_BID.iloc[0]["Open"])
    print("  Close-Openの合計:", self.df_BID["Close"].sum() - self.df_BID["Open"].sum())
    print("ASK:")
    print("  開始値:", self.df_ASK.iloc[0]["Open"])
    print("  終了値:", self.df_ASK.iloc[-1]["Close"])
    print("  終了値ー開始値:", self.df_ASK.iloc[-1]["Close"] - self.df_ASK.iloc[0]["Open"])
    print("  Close-Openの合計:", self.df_ASK["Close"].sum() - self.df_ASK["Open"].sum())

class MainObject:
  def __init__(self, pair, store = 100):
    self.pair = pair
    self.dts = []
    self.BID = []  # open
    self.ASK = []  # open
    self.position = None  # buy or sell or None
    self.average = None  # 平均建玉レート
    # self.order = []  # limit, stop, market, None
    # self.settlement = []  # limit, stop, market, None
    self.settlement_counter = 0
    self.limit = None
    self.stop = None
    self.ifd_limit = None
    self.ifd_stop = None
    # self.pips = 0
    self.pips = {
      "total": 0,
      "profit": 0,
      "loss": 0
    }
    self.start = None
    self.end = None
    self.store = store
  def _pips_add(self, pips):
    if pips > 0:
      self.pips["profit"] += pips
    elif pips < 0:
      self.pips["loss"] -= pips
    self.pips["total"] += pips
  def _get_incre(self, ASK=False):
    if self._get_len() == 0:
      return []
    else:
      incre = [None]
      for i in range(1, self._get_len()):
        if ASK:
          incre.append(self.ASK[i] - self.ASK[i-1])
        else:
          incre.append(self.BID[i] - self.BID[i-1])
      return incre
  def set_time(self, start:datetime.time, end:datetime.time):
    self.start = start
    self.end = end
    if self.start == self.end:
      raise Exception("The start and end are the same.")
  def _check_time(self, dt=None):
    if self.start == self.end == None:
      # 設定されていない場合は常にTrue
      return True
    # dtがNoneの場合はself.dtsの最終日時を使う
    if dt is None:
      dt = self.dts[-1]
    # dtがstartとendの間にあるかどうかをチェック
    if check_summer_time:
      diff = datetime.timedelta(hours=6)
    else:
      diff = datetime.timedelta(hours=7)
    # print(f"start: {self.start}, end: {self.end}, dt: {dt.time()}")
    # print(f"start: {time_and_timedelta_calculation(self.start, diff, minus=True)}, end: {time_and_timedelta_calculation(self.end, diff, minus=True)}, dt: {(dt-diff).time()}")
    # if self.start-diff <= (dt-diff).time() <= self.end-diff:
    if time_and_timedelta_calculation(self.start, diff, minus=True) <= (dt-diff).time() <= time_and_timedelta_calculation(self.end, diff, minus=True):
      return True
    else:
      return False
  def _check_data(self):
    if len(self.dts) != len(self.BID) or len(self.BID) != len(self.ASK):
      raise Exception("The length of the lists is different.")
    if self.position not in ["buy", "sell", None]:
      raise Exception("The position is invalid.")
    # if self.order not in ["limit", "stop", "market", None]:
    #   raise Exception("The order is invalid.")
    # if self.settlement not in ["limit", "stop", "market", None]:
    #   raise Exception("The settlement is invalid.")
  def _del(self):
    self._check_data()
    if len(self.dts) > self.store:
      self.dts = self.dts[-self.store:]
      self.BID = self.BID[-self.store:]
      self.ASK = self.ASK[-self.store:]
  def _get_len(self):
    self._check_data()
    return len(self.dts)
  def just_before(self, dt, BID, ASK):
    # print(self._get_len())
    # print(self.pips)
    # print(self.position)
    # データーを追加する
    self.dts.append(dt)
    self.BID.append(BID["Open"])
    self.ASK.append(ASK["Open"])
    # BIDとASKは辞書型でOpen, Close, High, Low, Diffを持つ
    if self._check_time():
      if self._get_len() <= 1:
        print("The length of the list is not enough.")
      else:
        incre = self._get_incre()
        if incre[-2]*incre[-1] < 0 and self.position is not None:
          # 決済
          if self.position == "buy":
            diff = self.BID[-1] - self.average
          elif self.position == "sell":
            diff = self.average - self.ASK[-1]
          else:
            raise Exception("The position is invalid.")
          if self.pair in ["USDJPY", "EURJPY", "GBPJPY"]:
            # self.pips += diff * 100
            self._pips_add(diff * 100)
          elif self.pair in ["EURUSD"]:
            # self.pips += diff * 10000
            self._pips_add(diff * 10000)
          else:
            raise Exception("The pair is invalid.")
          self.position = None
          self.settlement_counter += 1
        if self.position is None:
          # 新規注文
          if incre[-1] > 0:
            self.position = "buy"
            self.average = ASK["Open"]
          elif incre[-1] < 0:
            self.position = "sell"
            self.average = BID["Open"]
    else:
      # print("The time is not in the range.")
      pass
    self._del()
  def print_result(self):
    print("Result(pips):")
    print("  Profit:", self.pips["profit"])
    print("  Loss  :", self.pips["loss"])
    print("  Total :", self.pips["total"])
    print("  Rate  : {:.2f}%".format(self.pips["profit"] / (self.pips["profit"] + self.pips["loss"]) * 100))

def main():
  options = parse_args()
  pair="USDJPY"
  # pair="EURJPY"
  # pair="EURUSD"
  start_date = datetime.date(2023, 1, 1) 
  end_date = datetime.date(2024, 3, 1)
  DP = DataProvider(pair, start_date, end_date, rule="15T")
  DP.print_info()
  MO = MainObject(pair=pair)
  MO.set_time(datetime.time(10, 0), datetime.time(2, 0))
  while True:
    try:
      NEXT = DP.get_next()
    except StopIteration:
      break
    MO.just_before(NEXT["dt"], NEXT["BID"], NEXT["ASK"])
  # print("pips:", MO.pips)
  MO.print_result()
  # data = DP.get_next()
  # print(data["dt"])
  # print(data["dt"].__class__)
  

if __name__ == '__main__':
  main()
