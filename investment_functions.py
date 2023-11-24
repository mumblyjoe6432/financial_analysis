import matplotlib.pyplot as plt
import pdb
import pandas as pd
import seaborn as sns

#SOME VARIABLES
MAX_PRINCIPLE_ELIGIBLE_FOR_HMID = 750000
STANDARD_DEDUCTION = 27700
TOP_TAX_RATE = .35

#Let's check what happens after 30 years
#Initial Assumptions
INVESTMENT_RETURN_RATE = 6.0 #Unit is percent gain, so a value of 9.0 is a 9% annual gain
INITIAL_MORTGAGE_RATE = 4.25 #Unit is in percent, so a value of 4.25 is a 4.25% APR
MORTGAGE_FLOAT_RATE = 9 #Unit is in percent, so a value of 6.0 is 6% APR
INITIAL_EXTRA_MONTHLY_CASH = 2000 #Amount, in dollars, extra to invest
MORTGAGE_TERM_YEARS = 30 #Term of the morgage, in years
ARM_YEAR = 7 #This is the year number which the loan will start to float
YEARLY_RAISE_PERCENT = 2 #Unit is in percent, so a value of 3.0 is a 3.0% annual raise in the extra_monthly_cash + initial mortgage payment

def main():
    #Set up output variables
    output_data = {}
    mortgage_float_rates = [4,5,6,7,8,9]
    investment_return_rates = [4,5,6,7,8,9,10,11,12]
    for mortgage_float_rate in mortgage_float_rates:
        output_data[mortgage_float_rate] = {}
        for investment_return_rate in investment_return_rates:
            output_data[mortgage_float_rate][investment_return_rate] = run_simulation(mortgage_float_rate, investment_return_rate, False)

    #Now we have the data, but we need to put it into plottable form
    xs = []
    ys = []
    invest_path_advantages = []
    plot_data = {'Mortgage Float Rate':[], 'Investment Return Rate':[], 'Investment Path Advantage':[]}
    for mortgage_float_rate in mortgage_float_rates:
        for investment_return_rate in investment_return_rates:
            ipa = output_data[mortgage_float_rate][investment_return_rate]["Investment Path Total Net Worth"][-1] - output_data[mortgage_float_rate][investment_return_rate]["Invest Then Mortgage Payoff Path Total Net Worth"][-1]
            plot_data['Mortgage Float Rate'].append(mortgage_float_rate)
            plot_data['Investment Return Rate'].append(investment_return_rate)
            plot_data['Investment Path Advantage'].append(ipa)
            # xs.append(mortgage_float_rate)
            # ys.append(investment_return_rate)
            # invest_path_advantages.append(ipa)
    df = pd.DataFrame(plot_data)
    sns.scatterplot(data=df, x='Mortgage Float Rate', y='Investment Return Rate', hue='Investment Path Advantage', palette='coolwarm', marker = 's', s=10000, legend=False)
    for i in range(len(plot_data["Mortgage Float Rate"])):
        xval = plot_data["Mortgage Float Rate"][i]
        yval = plot_data["Investment Return Rate"][i]
        zval = round(plot_data["Investment Path Advantage"][i])
        plt.text(xval, yval, zval)
    plt.show()
    
#GUTS CONTAINED BELOW

#Class to work with mortgages
class Mortgage:
    def __init__(self, mortgage_amount, interest_rate, term_length_months):
        self.original_mortgage_amount = mortgage_amount
        self.principal = mortgage_amount
        self.interest_rate = interest_rate/100
        self.total_term_length_months = term_length_months
        self.payments_remaining = term_length_months
        self.calculate_monthly_payment()

    def calculate_monthly_payment(self):
        monthly_interest_rate = self.interest_rate/12
        self.monthly_payment = self.principal*(monthly_interest_rate*(1+monthly_interest_rate)**(self.payments_remaining)) / ((1+monthly_interest_rate)**(self.payments_remaining)-1)

    def make_monthly_payments(self, payments=1):
        extra_cash = 0
        for i in range(payments):
            extra_cash += self._make_monthly_payment()
        return extra_cash

    def make_lumpsum_payment(self, amount):
        self.principal -= amount

    def _make_monthly_payment(self):
        interest_for_payment = self.principal*self.interest_rate/12
        if self.principal > (self.monthly_payment - interest_for_payment):
            self.principal = self.principal - (self.monthly_payment - interest_for_payment)
            self.payments_remaining -= 1
            return 0
        else:
            extra_payment = (self.monthly_payment - interest_for_payment) - self.principal
            self.payments_remaining -= 1
            return extra_payment

    def change_interest_rate(self, interest_rate):
        self.interest_rate = interest_rate/100
        self.calculate_monthly_payment()

    def return_final_payment_amount(self):
        interest_for_payment = self.principal*self.interest_rate/12
        return interest_for_payment + self.principal

#Need a class to track investments
class Investment:
    def __init__(self, initial_investment, rate_of_return_yearly):
        self.total_value = initial_investment
        self.yearly_ror = rate_of_return_yearly
        self.monthly_ror = (1+self.yearly_ror/100)**(1/12)-1
        self.taxable_interest_income = 0

    def monthly_investment(self, amount):
        interest_gained = self.total_value*self.monthly_ror
        self.taxable_interest_income += interest_gained
        self.total_value += interest_gained
        self.total_value = self.total_value + amount

    def extra_investment(self, amount):
        self.total_value = self.total_value + amount

    def change_ror(self, rate_of_return_yearly):
        self.yearly_ror = rate_of_return_yearly
        self.monthly_ror = (1+self.yearly_ror/100)**(1/12)-1

#Class used to calculate the tax savings for the mortage interest deduction
def calculate_mortgage_interest_deduction_savings(principal, interest_rate):
    #DESCRIPTION
    #This function takes a given mortgage and returns the potential savings for the
    #Home Mortgage Interest Deduction (HMID)
    #INPUTS
    #principal - the amount remaining on the loan
    #interest_rate - in %, the APR interest rate. i.e. 6 would be 6%
    #OUTPUTS
    #Will return the dollar amount of in-pocket money you can save

    #Calculate the total qualified interest
    if principal > MAX_PRINCIPLE_ELIGIBLE_FOR_HMID:
        adjusted_principal = MAX_PRINCIPLE_ELIGIBLE_FOR_HMID
    else:
        adjusted_principal = principal
    total_qualified_interest = adjusted_principal * interest_rate / 100

    #If it's better to take the standard deduction, the savings is 0
    if total_qualified_interest < STANDARD_DEDUCTION:
        return 0
    
    #If the HMID is a better deal, return how much in-pocket money you save
    tax_savings = (total_qualified_interest - STANDARD_DEDUCTION) * TOP_TAX_RATE
    return tax_savings

#This runs a simulation for the 30 year team for all 3 different cases, based on the global variables

def run_simulation(mortgage_float_rate = MORTGAGE_FLOAT_RATE,
                   investment_return_rate = INVESTMENT_RETURN_RATE,
                   graph_output = False):
    #Initialize the accounts
    #NOTE: There are two different paths.
    # PATH1 is where you invest the extra cash in an investment account (Investment Path)
    # PATH2 is where you put the extra cash into an investment account and use that money to pay off as much of the mortgage as possible when the interest rate changes (Mortgage Payoff Path)
    # PATH3 is where you put the extra cash each month into paying off the mortgage
    mortgage_path1 = Mortgage(1440000, INITIAL_MORTGAGE_RATE, MORTGAGE_TERM_YEARS*12) #This is the mortgage class object for the Investment Path (PATH1)
    investment_path1 = Investment(0, investment_return_rate) #This is the investment account class object for the Investment Path (PATH1)
    mortgage_path2 = Mortgage(1440000, INITIAL_MORTGAGE_RATE, MORTGAGE_TERM_YEARS*12) #This is the mortgage class object for the Mortgage Payoff Path (PATH2)
    investment_path2 = Investment(0, investment_return_rate) #This is the investment account class object for the Mortgage Payoff Path (PATH2)
    mortgage_path3 = Mortgage(1440000, INITIAL_MORTGAGE_RATE, MORTGAGE_TERM_YEARS*12) #This is the mortgage class object for the Mortgage Payoff Path (PATH3)
    investment_path3 = Investment(0, investment_return_rate) #This is the investment account class object for the Mortgage Payoff Path (PATH3)

    #Here we initialize the output_data variable. It is just used to record the status of the accounts each month as we go
    #through the simulation
    output_data = {
                "Investment Path Mortgage Principal": [mortgage_path1.principal],
                "Investment Path Investment Value": [0],
                "Investment Path Total Net Worth": [0-mortgage_path1.principal],
                "Invest Then Mortgage Payoff Path Mortgage Principal": [mortgage_path2.principal],
                "Invest Then Mortgage Payoff Path Investment Value":[0],
                "Invest Then Mortgage Payoff Path Total Net Worth": [0-mortgage_path2.principal],
                "Mortgage Payoff Path Mortgage Principal": [mortgage_path2.principal],
                "Mortgage Payoff Path Investment Value":[0],
                "Mortgage Payoff Path Total Net Worth": [0-mortgage_path2.principal],
                }

    #A couple initial calculations for variables used:
    initial_payment_amount = mortgage_path2.monthly_payment #Recording the initial payment amount into a local variable
    total_monthly_cash = initial_payment_amount + INITIAL_EXTRA_MONTHLY_CASH #This is the total monthly cash which is important for later
    for year in range(1,MORTGAGE_TERM_YEARS+1,1):
        if year == 2: #In year two, we made a lumpsum payment (kind of accident)
            mortgage_path1.make_lumpsum_payment(18000)
            mortgage_path2.make_lumpsum_payment(18000)
            mortgage_path3.make_lumpsum_payment(18000)

        if year == ARM_YEAR+1: #This is the year the interest rate starts to float
            mortgage_path1.change_interest_rate(mortgage_float_rate)
            mortgage_path2.change_interest_rate(mortgage_float_rate)
            mortgage_path3.change_interest_rate(mortgage_float_rate)

            #Special event! For PATH2, we're going to dump our investments into the mortgage
            account_amount = investment_path2.total_value #Get the value of the investments thus far
            net_amount_after_taxes = account_amount - investment_path2.taxable_interest_income*TOP_TAX_RATE #Subtract the taxes
            mortgage_path2.make_lumpsum_payment(net_amount_after_taxes) #Make the payment on the mortgage
            investment_path2 = Investment(0, investment_return_rate) #Restart the investment account

        for month in range(1,13,1): #After the yearly calculations, we'll do the rest of the year's calculations by month
            #Let's figure out PATH1 first
            #First, we're going to pay the mortgage. extra_cash is normally zero, unless the mortgage is paid off
            extra_cash_path1 = mortgage_path1.make_monthly_payments()
            #Now we're going to figure out how much cash we have left including the extra monthly cash
            #It's worth noting that this can be negative depending if the mortgage payment went up
            extra_cash_balance_path1 = total_monthly_cash - mortgage_path1.monthly_payment + extra_cash_path1
            #Now, whatever cash we have left (perhaps negative, and we "take it out" of this investment)
            #we will put into the investment
            #print("Year %s Month %s Invest: %s"%(year, month, extra_cash_balance_path1))
            investment_path1.monthly_investment(extra_cash_balance_path1)

            #Now let's figure out PATH2
            #First, we're going to pay the mortgage. extra_cash is normally zero, unless the mortgage is paid off
            extra_cash_path2 = mortgage_path2.make_monthly_payments()
            #Now we're going to figure out how much cash we have left including the extra monthly cash
            #It's worth noting that this can be negative depending if the mortgage payment went up
            extra_cash_balance_path2 = total_monthly_cash - mortgage_path2.monthly_payment + extra_cash_path2
            #Now, we need some logic.
            if year > ARM_YEAR: #If we are floating interest rate, put all extra cash into the mortgage
                if mortgage_path2.principal < extra_cash_balance_path2: #If the mortgage is paid, invest the money!
                    mortgage_path2.make_lumpsum_payment(mortgage_path2.principal)
                    investment_path2.monthly_investment(extra_cash_balance_path2-mortgage_path2.principal)
                else: #If we still need to pay off the mortgage, put the money toward that
                    mortgage_path2.make_lumpsum_payment(extra_cash_balance_path2)
            else: #If we are still at the low intro rate on the ARM, put extra cash into investments
                investment_path2.monthly_investment(extra_cash_balance_path2)

            #Now let's figure out PATH3
            #First, we're going to pay the mortgage. extra_cash is normally zero, unless the mortgage is paid off
            extra_cash_path3 = mortgage_path3.make_monthly_payments()
            #Now we're going to figure out how much cash we have left including the extra monthly cash
            #It's worth noting that this can be negative depending if the mortgage payment went up
            extra_cash_balance_path3 = total_monthly_cash - mortgage_path3.monthly_payment + extra_cash_path3
            #Now a bit of logic
            if mortgage_path3.principal < extra_cash_balance_path3: #If the mortgage is paid, invest the money!
                mortgage_path3.make_lumpsum_payment(mortgage_path3.principal)
                investment_path3.monthly_investment(extra_cash_balance_path3-mortgage_path3.principal)
            else: #Otherwise put the extra cash into the mortgage as a lump sum
                mortgage_path3.make_lumpsum_payment(extra_cash_balance_path3)

            #Now record all the values
            output_data["Investment Path Mortgage Principal"].append(mortgage_path1.principal)
            output_data["Investment Path Investment Value"].append(investment_path1.total_value)
            output_data["Investment Path Total Net Worth"].append(investment_path1.total_value - mortgage_path1.principal)
            output_data["Invest Then Mortgage Payoff Path Mortgage Principal"].append(mortgage_path2.principal)
            output_data["Invest Then Mortgage Payoff Path Investment Value"].append(investment_path2.total_value)
            output_data["Invest Then Mortgage Payoff Path Total Net Worth"].append(investment_path2.total_value - mortgage_path2.principal)
            output_data["Mortgage Payoff Path Mortgage Principal"].append(mortgage_path3.principal)
            output_data["Mortgage Payoff Path Investment Value"].append(investment_path3.total_value)
            output_data["Mortgage Payoff Path Total Net Worth"].append(investment_path3.total_value - mortgage_path3.principal)
        total_monthly_cash += total_monthly_cash*(YEARLY_RAISE_PERCENT/100)

    if graph_output:
        #Graphing/Output
        x_axis = list(range(MORTGAGE_TERM_YEARS*12+1))
        fig, ax = plt.subplots()
        for dataset in output_data:
            ax.plot(x_axis, output_data[dataset], label=dataset)
        # ax.plot(x_axis, output_data["Investment Path Mortgage Principal"], label = "Investment Path Mortgage Principal")
        # ax.plot(output_data["Investment Path Investment Value"], label = "Investment Path Investment Value")
        # ax.plot(output_data["Mortgage Payoff Path Mortgage Principal"], label = "Mortgage Payoff Path Mortgage Principal")
        # ax.plot(output_data["Mortgage Payoff Path Investment Value"], label = "Mortgage Payoff Path Investment Value")
        # ax.plot(output_data["Investment Path Total Net Worth"], label = "Investment Path Total Net Worth")
        # ax.plot(output_data["Mortgage Payoff Path Total Net Worth"], label = "Mortgage Payoff Path Total Net Worth")
        ax.legend()
        plt.show()

    return output_data

if __name__ == "__main__":
    #run_simulation(True)
    main()