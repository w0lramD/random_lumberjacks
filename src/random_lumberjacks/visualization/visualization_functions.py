import functools
import math
import re
import pandas as pd
import seaborn as sns
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
import statsmodels.formula.api as smf
import statsmodels.stats.api as sms
import scipy.stats as scs


class Multiplot(object):
    """An object to quickly generate multiple plots for each column in a DataFrame"""

    def __init__(self, df, n_cols=3, figsize=(15, 15), style="darkgrid"):
        """Sets up the general parameters to be used across all graphs."""

        self.df = df.copy()
        self.columns = self.df.columns
        self.figsize = figsize
        self.set_cols(n_cols)
        self.style = style
        self.last_col = None

    def _multicol_plot_wrapper(func):
        """Decorator to be used to wrap plotting function to generate and plot
        multiple matplotlib figures and axes objects for multiple columns."""

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            self.fig, self.axes = self._generate_subplots()
            for self.ax_i, self.last_col in enumerate(self.columns):
                self._determine_ax()
                func(self, *args, **kwargs)
            plt.show()

        return wrapper

    def _determine_ax(self):
        """Sets current axis based on iterator and axes object. If only one
        column, it does not look for a column index."""

        row, col = self.ax_i // self.n_cols, self.ax_i % self.n_cols
        if self.n_cols == 1:
            self.last_ax = self.axes[row]
        elif self.n_rows == 1:
            self.last_ax = self.axes[col]
        else:
            self.last_ax = self.axes[row][col]

    def _generate_subplots(self):
        """Creates subplots based on current parameter attributes"""

        sns.set_style(self.style)
        return plt.subplots(nrows=self.n_rows, ncols=self.n_cols, figsize=self.figsize)

    def _set_rows(self, n_plots=False):
        """Determines the amount of row axes needed depending on the total
        plots and the column size"""

        if not n_plots:
            n_plots = self.df.columns.size
        self.n_rows = math.ceil(n_plots / self.n_cols)

    def _xyz(self, terms, iterable):
        """Grabs axis values from a dictionary and inserts the iterable into
        the first empty instance. Returns a dictionary of only filled axes."""

        x, y, z = terms.get("x"), terms.get("y"), terms.get("z")
        var_list = [x, y, z]
        for i, var in enumerate(var_list):
            if not var:
                var_list[i] = iterable
                break
        var_dict = {key: value for key, value in zip(["x", "y", "z"], filter(None, var_list))}
        return var_dict

    def _xyz_to_kwargs(self, kwargs, iterable, return_axes=False):
        axes = self._xyz(kwargs, iterable)
        new_kwargs = kwargs.copy()
        new_kwargs.update(axes)
        if return_axes:
            return new_kwargs, axes
        else:
            return new_kwargs

    def modify_col_list(self, columns, drop=True):
        """Allows changes to what columns will be graphed. Default is to drop, but
        can add columns as well."""

        if drop:
            self.columns = self.columns.drop(columns)
        else:
            columns = pd.Index(columns)
            self.columns = self.columns.append(columns)
            self.columns = self.columns.drop_duplicates()
        self._set_rows()

    def set_cols(self, n_cols):
        """Changes the amount of plot columns to display and adjusting the
        rows needed accordingly."""

        self.n_cols = n_cols
        self._set_rows()

    @_multicol_plot_wrapper
    def sb_multiplot(self, func, kwargs={}, default_axis=False):
        """Flexible way of calling iterating through plots of a passed
        Seaborn function. Default axis determines what axis the iterated
        variables will take on. Leave blank for one dimensional plots."""

        if default_axis and kwargs:
            kwargs = self._xyz_to_kwargs(kwargs, self.last_col)
            return func(data=self.df, ax=self.last_ax, **kwargs)
        else:
            return func(self.df[self.last_col], ax=self.last_ax, **kwargs)


class LinearityTest(Multiplot):
    """An object to run linearity tests/plots to see if assumptions are met on individual features for linear and
    logistic regression."""

    def __init__(self, df, n_cols=3, figsize=(15, 15), style="darkgrid"):
        """Sets up the general parameters to be used across all graphs."""

        super().__init__(df, n_cols, figsize, style)
        self._fix_col_names()
        self.linearity_plots = 5
        self.logistic_plots = 2

    def _calc_sigmoid(self, x_vals, model):
        """A quick calculation of the sigmoid across an array"""

        m, b = model.params[1], model.params[0]
        logodds = m*x_vals + b
        odds = math.e ** logodds
        return odds/(1+odds)

    def _create_sigmoid(self, model, df, column):
        """Quickly creates a line across an array of x values based on the intercept/coefficients of the model."""

        samples = len(df[column])
        xmin, xmax = df[column].min(), df[column].max()
        sigmoid = np.zeros([2, samples])
        sigmoid[0] = np.array(np.arange(xmin, xmax, (xmax - xmin) / samples))
        print(sigmoid[0])
        sigmoid[1] = self._calc_sigmoid(sigmoid[0], model)
        return sigmoid

    def _fix_col_names(self):
        """Whitespace will break the tests in the statsmodels formula api so this replaces column names with
        underscores"""

        columns = {column:re.sub('\W', "_", column) for column in self.df.columns}
        self.df.rename(columns=columns, inplace=True)

    def _plot_qq_manual(self, comparison_df):
        """Class no longer uses this. Replaced with the generated plots from
        statsmodels."""

        columns = comparison_df.columns
        ax_kwargs = {x: y for x, y in zip(["x", "y"], columns)}
        qq_data = pd.DataFrame(columns=columns)
        for column in columns:
            qq_data[column] = np.quantile(comparison_df[column], np.arange(0, 1, .01))
        return sns.scatterplot(data=qq_data, ax=self.last_ax, **ax_kwargs)

    def _plot_ccpr(self, model):
        """Creates a Component and Component Plus Residual plot"""

        sm.graphics.plot_ccpr(model, 1, ax=self.last_ax)
        self.last_ax.lines[1].set_color("r")

    def _plot_qq(self, model):
        """Creates a qq plot to test residuals for normality."""

        sm.graphics.qqplot(model.resid, dist=scs.norm, line='45', fit=True, ax=self.last_ax)

    def _plot_logistic(self, model, df, column, target, logodds=False):
        """Will either plot the logistic regression line of the probability or logodds."""
        if logodds:
            sns.scatterplot(x=column, y=target, hue="actual", data=df, ax=self.last_ax)
        else:
            line = self._create_sigmoid(model, df, column)
            sns.scatterplot(x=column, y="actual", data=df, ax=self.last_ax)
            sns.lineplot(x=line[0], y=line[1], ax=self.last_ax, **{"color": "r"})

    def _plot_resid(self, model):
        """Plots a scatterplot of residuals along a dependant variable"""

        resid, x = model.resid, self.df[self.last_col]
        line = np.array([[x.min(), 0], [x.max(), 0]]).T
        sns.scatterplot(x, resid, ax=self.last_ax)
        sns.lineplot(x=line[0], y=line[1], ax=self.last_ax, **{"color": "r"})
        self.last_ax.set_title('Residual_plot')
        self.last_ax.set_ylabel('Residual values')

    def _plot_resid_hist(self, model):
        """Plots a histogram of residual values."""

        sns.distplot(model.resid, ax=self.last_ax)
        self.last_ax.set_title('Residual_distribution')
        self.last_ax.set_xlabel('Residual values')

    def _plot_yfit_y_pred_v_x(self, model):
        """Plots a y and y fitted vs x graph"""

        sm.graphics.plot_fit(model, 1, ax=self.last_ax)

    def _prediction_df(self, predictions, actual):
        """Currently unused function that combines predictions and test data
        into a single dataframe."""

        columns, pred_list = ["predicted", "actual"], np.stack((predictions, actual))
        return pd.DataFrame(pred_list.T, columns=columns)

    def _predictions_logit(self, model, column, target):
        """Extracts logistic regression predictions from a model and places them in a dataframe along with the
        independant variable and the actual result"""

        logodds = model.predict(self.df[column], linear=True)
        df = self._prediction_df(logodds, self.df[target])
        df[column] = self.df[column]
        df.rename(columns={"predicted": target}, inplace=True)
        return df

    def _sb_linearity_plots(self, model, column, target, logistic=False):
        """For loop that creates the axes and plots for linearity checks"""

        self.fig, self.axes = self._generate_subplots()
        if logistic:
            plots = self.logistic_plots
            scatterpoints = self._predictions_logit(model, column, target)
            args = [model, scatterpoints, column, target]
            switch_function = self._sb_logistic_switch
        else:
            plots = self.linearity_plots
            args = [model]
            switch_function = self._sb_linearity_switch

        for self.ax_i in np.arange(plots):
            self._determine_ax()
            switch_function(self.ax_i, *args)
        plt.show()

    def _sb_linearity_switch(self, i, model):
        """Uses if statement switches to allow different functions to be inserted
        in the for loop that dynamically sets the axes."""

        if i == 0:
            self._plot_yfit_y_pred_v_x(model)
        if i == 1:
            self._plot_resid(model)
        if i == 2:
            self._plot_ccpr(model)
        if i == 3:
            self._plot_resid_hist(model)
        if i == 4:
            self._plot_qq(model)

    def _sb_logistic_switch(self, i, model, scatterpoints, column, target):
        """Uses if statement switches to allow different functions to be inserted
        in the for loop that dynamically sets the axes."""

        if i == 0:
            self._plot_logistic(model, scatterpoints, column, target, logodds=True)
        if i == 1:
            self._plot_logistic(model, scatterpoints, column, target)

    def _test_goldfeld_quandt(self, model, lq, uq):
        """Runs a Goldfeld Quandt test for heteroscadasticity."""

        column = self.last_col
        lwr = self.df[column].quantile(q=lq)
        upr = self.df[column].quantile(q=uq)
        middle_idx = self.df[(self.df[column] >= lwr) & (self.df[column] <= upr)].index

        idx = [x - 1 for x in self.df.index if x not in middle_idx]
        gq_labels = ['F statistic', 'p-value']
        gq = sms.het_goldfeldquandt(model.resid.iloc[idx], model.model.exog[idx])
        return list(zip(gq_labels, gq))

    def _test_jarque_bera(self, model):
        """Runs a Jarque-Bera test for normality"""

        jb_labels = ['Jarque-Bera', 'Prob', 'Skew', 'Kurtosis']
        jb = sms.jarque_bera(model.resid)
        return list(zip(jb_labels, jb))

    def _test_regression_metrics_logit(self, model, column, target):
        """Runs various statistical tests and prints the values for logistic regression"""

        pr_squared, ll = model.prsquared, model.llf
        llnull, p_values = model.llnull, model.pvalues
        coef, intercept = model.params[1], model.params[0]

        print(f"{column} predicting {target}:")
        print(f"Pseudo R2: {pr_squared}, Log Likelihood: {ll}, Null Log Likelihood: {llnull}:")
        print(f"Coeficient: {coef}, Intercept: {intercept}")
        print("")
        print("P-values:")
        print(p_values)

    def _test_regression_metrics_ols(self, model, column, target):
        """Runs various statistical tests and prints the values for ols linear regression"""

        r_squared, mse = model.rsquared, model.mse_model,
        rmse, p_values = math.sqrt(mse), model.pvalues
        coef, intercept = model.params[1], model.params[0]

        jb = self._test_jarque_bera(model)
        gq = self._test_goldfeld_quandt(model, .45, .55)

        print(f"{column} predicting {target}:")
        print(f"R2: {r_squared}, MSE: {mse}, RMSE: {rmse}:")
        print(f"Coeficient: {coef}, Intercept: {intercept}")
        print("")
        print("P-values:")
        print(p_values)
        print("")
        print("Jarque-Bera:")
        print(*jb)
        print("")
        print("Goldfeld-Quandt:")
        print(*gq)

    def sb_linearity_test(self, column, target, logistic=False):
        """Tests for linearity along a single independant feature and plots
        associated visualizations."""

        column, target = re.sub('\W', "_", column), re.sub('\W', "_", target)
        self.last_col = column
        formula = f'{target}~{column}'
        if logistic:
            self._set_rows(self.logistic_plots)
            model = smf.logit(formula=formula, data=self.df).fit()
            self._test_regression_metrics_logit(model, column, target)
        else:
            self._set_rows(self.linearity_plots)
            model = smf.ols(formula=formula, data=self.df).fit()
            self._test_regression_metrics_ols(model, column, target)
        self._sb_linearity_plots(model, column, target, logistic)

        # Resets rows to their defaults
        self._set_rows()


def print_full(x):
    """Dynamically changes the amount of max visible rows for a pandas object."""

    pd.set_option('display.max_rows', len(x))
    display(x)
    pd.reset_option('display.max_rows')


def plot_stacked_proportion(df, column, target, blend=0, style="darkgrid", palette="muted", x_dict=None):
    """Creates a stacked bar chart normalized by proportion, and scaled
    horizontally by the representation of the total data that is contained
    by each parameter. The blend argument will allow you to attenuate this
    effect and ranges from zero to one."""
    sns.set_style(style)
    sns.set_palette(palette)
    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(15, 10))

    # Groups the dataframe where the index is the values of the independant column
    # and the total counts of each dependant variable are the columns.
    grouped = df.groupby([column, target])[column].count().unstack()

    # Calculates the respective size for each group along with the total size of
    # the sample.
    totals = grouped.sum(axis=1)
    n, n_col = totals.sum(), totals.size

    # Creates ratios of the sample size for the groups within your independant variable
    # and attenuates the differences based on the blend variable.
    sample_ratios = totals / n
    blended = blend / n_col + sample_ratios * (1 - blend)

    # Notmalizes the counts of the target variable to proportions instad of raw counts.
    proportions = grouped.divide(totals, axis=0)

    plot = proportions.plot(kind='bar', stacked=True, ax=ax)

    # Dynamically gets the sum total width of the bars based on the current plot.
    bar_width, n_bars = plot.containers[0][0].get_width(), len(plot.containers[0])
    agg_width = bar_width * n_bars
    whitespace = n_col - agg_width
    coord = 0

    # Loops through the matplotlib objects modifying their horizontal scale based
    # on the proportion of values in the sample and the blend parameter.
    for i in np.arange(n_col):
        for j in np.arange(len(plot.containers)):
            if i == 0:
                offset = -bar_width / 2
            elif j == 0:
                offset += new_width
            bar = plot.containers[j][i]
            new_width = agg_width * blended[i]
            gap = whitespace / n_col * i
            bar.set_width(new_width)
            bar.set_x(gap + offset)
    if x_dict:
        x_ticks = [x_dict.get(idx, idx) for idx in proportions.index]
        plot.set_xticklabels(x_ticks)
    plt.show()


#Changes long numeric values and replaces them with more human readable abbreviations.
def scale_units(value):
    if value < .99:
        new_val = str(round(value,3))
    elif value < 1000:
        new_val = str(round(value))
    elif value < 1000000:
        new_val = str(round(value/1000))+"k"
    elif value < 1 * 10**9:
        new_val = str(round(value/(10**6)))+"M"
    elif value < 1 * 10**12:
        new_val = str(round(value/(10**9)))+"B"
    elif value < 1 * 10**15:
        new_val = str(round(value/(10**12)))+"T"
    else:
        new_val = str(value)
    return new_val

#Inverts the log functions put on features. To be applied on ticks, so that the scale is visually condensed but the values
# are human readable.
def unlog_plot(values, base):
    to_series = pd.Series(values)
    exponented = base**to_series
    return exponented.map(scale_units).values.tolist()

#Shows the full breadth of possilbe values and nans for a column of a dataframe.
def full_value_counts(df, column):
    unique, total = df[column].unique().size, df[column].size
    totalna = df[column].isna().sum()
    percent_na = totalna/total
    print(f"There are {unique} unique values with {totalna} nan values making up {percent_na*100:.1f}%")
    for value, count in df[column].value_counts().iteritems():
        print(f"{count}-{value} --{count/total*100:.2f}%")

# Modifications to masked heatmap parameters from lecture notes.
def trimmed_heatmap(df, columns, font_scale=1, annot=True, figsize=(15,10)):
    plt.figure(figsize=figsize)
    corr = df[columns].corr()
    sns.set(style="white")

    # Generate a mask for the upper triangle
    mask = np.zeros_like(corr, dtype=np.bool)
    mask[np.triu_indices_from(mask)] = True

    # Set up the matplotlib figure
    f, ax = plt.subplots(figsize=(11, 9))

    # Generate a custom diverging colormap
    cmap = sns.diverging_palette(220, 10, as_cmap=True)
    sns.set_context('talk', font_scale=font_scale)

    # Draw the heatmap with the mask and correct aspect ratio
    sns.heatmap(corr, mask=mask, cmap=cmap, vmax=.95, center=0,
                square=True, linewidths=.5, cbar_kws={"shrink": .5}, annot=annot)

    return plt.show()

def show_feature_importances(model, df, figsize=(14, 12), palette=None, font_scale=1, ascending=False, rows=12, style="darkgrid"):
    sns.set_style(style)
    f, ax = plt.subplots(figsize=figsize)
    sns.set(font_scale=font_scale)
    importance = pd.DataFrame(model.feature_importances_, index=df.columns).reset_index()
    importance.columns = pd.Index(["Feature", "Importance"])
    sns.barplot(y="Feature", x="Importance", data=importance.sort_values("Importance",ascending=ascending).iloc[0:rows],
                palette=palette, ax=ax)
