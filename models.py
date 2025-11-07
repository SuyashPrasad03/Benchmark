import google.generativeai as genai

# Make sure your API key is configured
genai.configure(api_key="AIzaSyDMpItrNwmI0t-nOBjaJHn39220TdooCY4")

print("--- Models available for 'generateContent' ---")

try:
    for model in genai.list_models():
        # Check if the model supports the 'generateContent' method
        if 'generateContent' in model.supported_generation_methods:
            print(model.name)
            
except Exception as e:
    print(f"An error occurred: {e}")