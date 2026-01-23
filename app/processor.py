import pandas as pd
import numpy as np
import matplotlib
# CRITICAL: Use the 'Agg' backend to prevent the server from trying 
# to open a GUI window, which causes hangs and silent refreshes.
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import io, base64

class DataService:
    PLOT_CONFIG = {
        'countplot': {'lib': 'seaborn', 'desc': 'Shows counts of observations in categorical bins.'},
        'boxplot': {'lib': 'seaborn', 'desc': 'Displays distribution and outliers.'},
        'histplot': {'lib': 'seaborn', 'desc': 'Shows frequency distribution (Histogram).'},
        'scatterplot': {'lib': 'seaborn', 'desc': 'Relationship between two numeric variables.'},
        'pie': {'lib': 'matplotlib', 'desc': 'Numerical proportions in a circle.'}
    }

    @staticmethod
    def _fig_to_base64(plt_obj):
        img = io.BytesIO()
        plt_obj.savefig(img, format='png', bbox_inches='tight')
        img.seek(0)
        encoded = base64.b64encode(img.getvalue()).decode('utf8')
        plt_obj.close()
        return encoded

    @staticmethod
    def analyze_dataframe(df):
        """
        Calculates stats and generates initial Auto-EDA visuals.
        Ensures 'visuals' key ALWAYS exists to prevent Jinja2 errors.
        """
        # 1. Stats Table
        stats_table = df.describe(include='all').round(2).fillna('').to_html(
            classes='table table-sm table-hover border-0'
        )

        # 2. Initialize Visuals Dictionary
        visuals = {}
        numeric_df = df.select_dtypes(include=[np.number])

        # 3. Generate Automatic Visuals if numeric data exists
        if not numeric_df.empty:
            # Heatmap
            if numeric_df.shape[1] >= 2:
                plt.figure(figsize=(8, 6))
                sns.heatmap(numeric_df.corr(), annot=True, cmap='coolwarm', fmt=".2f")
                plt.title("Correlation Heatmap")
                visuals['heatmap'] = DataService._fig_to_base64(plt)
            
            # Distribution of first numeric column
            plt.figure(figsize=(8, 6))
            sns.histplot(numeric_df.iloc[:, 0], kde=True, color='blue')
            plt.title(f"Distribution: {numeric_df.columns[0]}")
            visuals['distribution'] = DataService._fig_to_base64(plt)

        # 4. Return the complete dictionary structure
        return {
            "all_cols": list(df.columns),
            "plot_options": DataService.PLOT_CONFIG,
            "stats_table": stats_table,
            "visuals": visuals  # <--- THIS MUST BE PRESENT
        }


    @staticmethod
    def generate_custom_plot(df, plot_type, x_col, y_col=None):
        """
        Dynamic Plot Engine with 'Debug Mode' Exception Handling.
        Validates the plot type and parameter compatibility.
        """
        # 1. Validation: Does the plot exist in our supported library?
        if plot_type not in DataService.PLOT_CONFIG:
            raise Exception(f"No such plot can be plotted: '{plot_type}' is not supported.")

        plt.figure(figsize=(10, 6))
        sns.set_style("whitegrid") # Sets a professional theme for Seaborn plots
        
        try:
            config = DataService.PLOT_CONFIG[plot_type]
            
            # 2. Logic for Seaborn Library
            if config['lib'] == 'seaborn':
                # Dynamically retrieve the function from the seaborn module
                plot_func = getattr(sns, plot_type)
                
                if y_col and y_col != "None":
                    plot_func(data=df, x=x_col, y=y_col)
                else:
                    plot_func(data=df, x=x_col)
            
            # 3. Logic for Matplotlib Library (e.g., Pie Charts)
            elif config['lib'] == 'matplotlib':
                if plot_type == 'pie':
                    counts = df[x_col].value_counts()
                    plt.pie(counts, labels=counts.index, autopct='%1.1f%%', startangle=140)
                    plt.axis('equal') # Ensures pie is drawn as a circle
                else:
                    plt.plot(df[x_col])

            plt.title(f"{plot_type.capitalize()} Analysis of {x_col}", fontsize=14, pad=20)
            
            # 4. Success: Return encoded image
            return DataService._fig_to_base64(plt)

        except Exception as e:
            plt.close()
            # This is the detailed exception you requested for debugging
            raise Exception(f"No such plot can be plotted: Technical Error -> {str(e)}")
        



    
import pandas as pd
import os

class TransformationService:
    @staticmethod
    def get_null_report(df):
        null_counts = df.isnull().sum()
        return {col: int(count) for col, count in null_counts.items() if count > 0}

    @staticmethod
    def apply_transform(df, action, params):
        try:
            df_copy = df.copy()
            if action == 'dropna_col':
                col = params.get('column')
                df_copy = df_copy.dropna(subset=[col])
            elif action == 'fillna_col':
                col = params.get('column')
                val = params.get('value', 0)
                df_copy[col] = df_copy[col].fillna(val)
            elif action == 'drop_col':
                col = params.get('column')
                if col in df_copy.columns:
                    df_copy = df_copy.drop(columns=[col])
            elif action == 'groupby':
                g_col = params.get('group_by')
                a_col = params.get('agg_col')
                func = params.get('agg_func', 'mean')
                # Grouping creates a new dataframe structure
                df_copy = df_copy.groupby(g_col)[a_col].agg(func).reset_index()

            return df_copy, None
        except Exception as e:
            return df, str(e)