from modal import Image, Stub, web_endpoint, Secret
from typing import Dict
import os

datascience_image = (
    Image.debian_slim(python_version="3.10")
    .pip_install("pandas==2.2.0", "numpy", "sentence_transformers", "openai", "bertopic", "safetensors", "py-readability-metrics", "nltk")
)

stub = Stub("sentence_comparison")


# @stub.function()
# @web_endpoint()
# async def main():
#     print("the square is", square.remote(42))

@stub.function(image=datascience_image)
@web_endpoint(method="POST")
def readability(item : Dict):
    from readability import Readability
    import nltk
    nltk.download('punkt')
    r = Readability(item['text'])
    fk = r.flesch_kincaid()
    return {"readability" : fk.score, "grade_level" : fk.grade_level}

@stub.function(secrets=[Secret.from_name("my-openai-secret")], image=datascience_image)
@web_endpoint(method="POST")
def response(item : Dict):
    from sentence_transformers import SentenceTransformer, util
    model = SentenceTransformer("all-MiniLM-L6-v2")
    # topic_model = BERTopic.load("MaartenGr/BERTopic_Wikipedia")
    # topics, probabilities = topic_model.transform(item['text'])

    from openai import OpenAI
    print("running")
    client = OpenAI()

    chat_completion = client.chat.completions.create(
        model="gpt-4-0125-preview",
        messages=[
            {
                "role": "system",
                "content": 'Generate a clear and concise summary of the text below. Capture the main ideas encapsulated in the text. Avoid using excess words when unneeded.',
            },
            {
                "role": "user",
                "content": item['text']
            }
        ]
    )

    embeddings1 = model.encode(chat_completion.choices[0].message.content)
    embeddings2 = model.encode(item['user_input'])

    cosine_scores = util.cos_sim(embeddings1, embeddings2)

    chat_completion2 = client.chat.completions.create(
        model="gpt-4-0125-preview",
        messages=[
            {
                "role" : "system",
                "content" : "Read through the reader's summary of the passage and provide feedback on how good their summary was compared to the actual literature. Provide areas where they conducted their summary well and areas where their summaries could improve."
            },
            {
                "role" : "system",
                "content" : "This is the actual literature:" + item['text']
            },
            {
                "role" : "user",
                "content" : item['user_input']
            }
        ]
    )

    return {"model_summary" : chat_completion.choices[0].message.content, "model_response" : chat_completion2.choices[0].message.content, "cosine_scores" : float(cosine_scores[0][0])}

@stub.function(image=datascience_image)
@web_endpoint(method="POST")
def find_topics(item : Dict):
    from bertopic import BERTopic

    topic_model = BERTopic.load("MaartenGr/BERTopic_Wikipedia")

    topics, probabilities = topic_model.transform(item['text'])

    topic_to_use = topics[0]
    l = topic_model.get_topic(topic_to_use)
    ts = [i[0] for i in l]

    return {"Passage_topics" : ts}