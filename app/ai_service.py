import google.generativeai as genai
import os

class AIService:
    @staticmethod
    def get_data_insights(df_summary, filename):
        """
        Logic: Takes a text summary of the Pandas data and 
        asks Gemini for a professional analysis.
        """
        # 1. Initialize Gemini with your API Key
        api_key = os.environ.get("AIzaSyD8TOE54JP_4amAak76xQdKmOXNTbMLdQY")
        if not api_key:
            return "AI Insights unavailable: Missing API Key."

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # 2. Prepare the "Context" (What Gemini needs to know)
        prompt = f"""
        You are a senior data analyst. I have a dataset named '{filename}'.
        Here is the statistical summary of the data:
        {df_summary}
        
        Please provide:
        1. A 2-sentence summary of what this data represents.
        2. Three key trends or anomalies you notice.
        3. Two suggestions for specific charts I should create to understand this better.
        Keep the tone professional and concise.
        """

        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"AI Error: {str(e)}"
