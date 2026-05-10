import re

with open('/Users/kxq/Desktop/BUAA-SE-AID/AIDetector/code/frontend/frontend-user/src/pages/upload.vue', 'r') as f:
    content = f.read()

# Replace if (payload.if_use_llm && selectedLlmModel.value) with if (selectedLlmModel.value)
content = re.sub(
    r"if \(payload\.if_use_llm && selectedLlmModel\.value\) payload\.llm_model_name = selectedLlmModel\.value",
    r"if (selectedLlmModel.value) payload.llm_model_name = selectedLlmModel.value",
    content
)

with open('/Users/kxq/Desktop/BUAA-SE-AID/AIDetector/code/frontend/frontend-user/src/pages/upload.vue', 'w') as f:
    f.write(content)

