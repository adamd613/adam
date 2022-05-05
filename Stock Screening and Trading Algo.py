#Packages
import pandas as pd
from pandas_datareader import data
import datetime as dt
from datetime import timedelta, date
import matplotlib.pyplot as plt
from scipy import stats

if date.today().weekday() <=4:
    #Variables
    dateRangeVar = 180
    slopeThresh = .1
    varThresh = .05
    peakThresh = 10
    troughThresh = 10
    buyAmt = 100
    sellAmt = 100
    newOrOld = 'old'
    startingMoney = 10000

    #(yes/no) Calculate Slope and Var thresh?
    slopeVarCalc = 'yes'

    #make sure to enter your path
    excelOutputFolder = r'C:\Users\yourName\Desktop\\'

    #Create Clean Reset DF
    statsDFBlank = pd.DataFrame(columns = ['Symbol', 'LastPrice', 'Days', 'StDev', 'Avg', 'Slope', 'Std/Avg', '#ofPeaks', '#ofTroughs'])
    statsDF = statsDFBlank

    #set date range
    endDate = date.today()
    dateRange = dt.timedelta(dateRangeVar)
    startDate = endDate - dateRange

    #Pull all S&P stocks
    wiki = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
    w = wiki[0]
    w = w['Symbol']
    w = w.reset_index()
    iterations = len(w)

    #Generate Export DF
    for x in range(iterations): 
        try:
            #Pick a ticker
            myTicker = w['Symbol'].iloc[x]

            #List Prices
            Prices = data.DataReader([myTicker], 'yahoo', start=startDate, end=endDate)         
            Prices = Prices['Adj Close']
            Prices = Prices.reset_index()

            #Find Stats
            stdPrice = Prices.std()[myTicker]
            avgPrice = Prices.mean()[myTicker]
            tradeDays = Prices.count()[myTicker]

            #Total Peaks and Troughs
            Prices['Peak'] = Prices[myTicker].apply(lambda x: 1 if x >= (avgPrice + stdPrice)  else 0)
            Prices['Trough'] = Prices[myTicker].apply(lambda x: 1 if x <= (avgPrice - stdPrice)  else 0)

            #Assign Peaks and Troughs
            totalPeaks = Prices.sum()['Peak']
            totalTroughs = Prices.sum()['Trough']

            #Find slope
            slope, intercept, r, p, se = stats.linregress(Prices.index, Prices[myTicker])

            #Select most recent price
            mostrecent = Prices[myTicker].iloc[len(Prices)-1]

            #How volitaile
            percentStd = stdPrice / avgPrice

            #Add Export Data
            exData = {'Symbol': myTicker,
                'LastPrice': mostrecent,
                'Days': tradeDays,
                'StDev': stdPrice,
                'Avg': avgPrice,
                'Slope': slope,
                'Std/Avg': percentStd,
                '#ofPeaks': totalPeaks,
                '#ofTroughs': totalTroughs}
            statsDF = statsDF.append(exData, ignore_index = True)
        except:
            continue

    #generate describe df
    statsStatsDF = statsDF.describe()

    #functions to set auto-limits
    if slopeVarCalc == 'yes':
        varThresh = statsStatsDF['Std/Avg'].iloc[4]
        slopeThresh = statsStatsDF['Slope'].iloc[5]
        peakThresh = statsStatsDF['#ofPeaks'].iloc[5]
        troughThresh = statsStatsDF['#ofTroughs'].iloc[5]

    #apply Buy and Sell Price and Logic
    statsDFTwo = statsDF
    statsDFTwo['buyPrice'] = statsDFTwo['Avg'] - statsDFTwo['StDev']
    statsDFTwo['sellPrice'] = statsDFTwo['Avg'] + statsDFTwo['StDev']
    statsDFTwo.loc[statsDFTwo['LastPrice'] <= statsDFTwo['buyPrice'], 'Buy?'] = 'yes' 
    statsDFTwo.loc[statsDFTwo['LastPrice'] >= statsDFTwo['sellPrice'], 'Sell?'] = 'yes'

    statsDFTwo=statsDFTwo.fillna('no')

    def f(row):
        if row['Buy?'] == 'yes' or row['Sell?'] == 'yes':
            val = 'yes'
        else:
            val = 'no'
        return val

    statsDFTwo['Buy or Sell?'] = statsDFTwo.apply(f, axis=1)

    def s(row):
        if abs(row['Slope']) <= slopeThresh and row['Std/Avg'] >= varThresh and row['#ofPeaks'] >= peakThresh and row['#ofTroughs'] >= troughThresh:
            val = 'yes'
        else:
            val = 'no'
        return val
    statsDFTwo['Qualifying Stock?'] = statsDFTwo.apply(s, axis=1)

    #filter  for only reccomended buys and sells
    statsDFThree = statsDFTwo[statsDFTwo['Qualifying Stock?'] == 'yes']

    #Export all data to excel
    #statsDF.to_excel(excelOutputFolder+"StockStatsExport.xlsx")
    statsDFTwo.to_excel(excelOutputFolder+"StockStatsExportwithCalcs.xlsx")
    statsDFThree.to_excel(excelOutputFolder+"StockStatsExportwithCalcsRefined.xlsx")   

    #------BEGIN CODE FOR TRADING-----

    #Function to reset Owned Stocks
    if newOrOld == 'new':
        stockLedger = pd.DataFrame(columns = ['Date', 'Buy/Sell', 'Symbol', 'Price', 'Shares', 'Amount', 'cashBalance'])
        AccValTrend = pd.DataFrame(columns = ['Date', 'Total Account Value'])
        startingBalance = startingMoney
        newBal = startingBalance
    elif newOrOld == 'old':
        stockLedger = pd.read_excel(excelOutputFolder+"Stock Ledger.xlsx", index_col=0)
        AccValTrend = pd.read_excel(excelOutputFolder+"Acc Value Trend.xlsx", index_col=0)
        aggHoldings = pd.read_excel(excelOutputFolder+"Current Holdings.xlsx", index_col=0)
        newBal = aggHoldings[aggHoldings['Symbol'] == 'Cash']['value']
        newBal = int(newBal)        

    #Function to place a trade
    def placeTrade(action, amount, ticker):
        global newBal
        global stockLedger

        sharePrice = statsDFTwo[statsDFTwo['Symbol']==ticker]['LastPrice']
        sharePrice = int(sharePrice)

        Date = endDate
        if action == 'buy':
            newBal = newBal - amount  
            shareQuantity = amount / sharePrice
        elif action == 'sell':
            newBal = newBal + amount 
            shareQuantity = amount / sharePrice *-1

        trade = {'Date': Date,
            'Buy/Sell': action,
            'Symbol': ticker,
            'Price': sharePrice,
            'Shares': shareQuantity,
            'Amount': amount,
            'cashBalance': newBal}

        stockLedger = stockLedger.append(trade, ignore_index = True)
        return stockLedger

    #Place trades here:
    loopsDF = statsDFThree['Symbol']
    loopsDF = loopsDF.reset_index()
    loops = len(loopsDF)
    for y in range(loops): 
        try:
            #Pick a ticker
            tradeTicker = statsDFThree['Symbol'].iloc[y]
            buyIndicator = statsDFThree['Buy?'].iloc[y]
            sellIndicator = statsDFThree['Sell?'].iloc[y]
            if buyIndicator == 'yes':
                placeTrade('buy', buyAmt, tradeTicker) 
            elif sellIndicator == 'yes':
                placeTrade('sell', sellAmt, tradeTicker) 
            else:
                continue
        except:
            continue

    #Save Stock Ledger
    stockLedger.to_excel(excelOutputFolder+"Stock Ledger.xlsx")  

    #Compile Current Holdings
    #aggHoldings = pd.read_excel(excelOutputFolder+"Current Holdings.xlsx", index_col=0)
    aggHoldings = stockLedger.groupby(['Symbol']).agg({'Shares':sum,'Date':max})
    aggHoldings = aggHoldings.reset_index()
    aggHoldings = aggHoldings.set_index('Symbol').join(statsDFTwo.set_index('Symbol'))
    aggHoldings = aggHoldings.reset_index()
    aggHoldings = aggHoldings[['Symbol','Shares','Date','LastPrice']]
    aggHoldings['value'] = aggHoldings['Shares'] * aggHoldings['LastPrice']
    #Add Cash Reccord
    cashReccord = {'Symbol': 'Cash',
        'Shares': newBal,
        'Date': endDate,
        'LastPrice': 1,
        'value': newBal}
    aggHoldings = aggHoldings.append(cashReccord, ignore_index = True)
    aggHoldings.to_excel(excelOutputFolder+"Current Holdings.xlsx")  

    #Trend Total Value
    totalValue = aggHoldings['value'].sum()
    TotalReccord = {'Date': endDate,
        'Total Account Value': totalValue}
    AccValTrend = AccValTrend.append(TotalReccord, ignore_index = True)
    AccValTrend.to_excel(excelOutputFolder+"Acc Value Trend.xlsx")  
