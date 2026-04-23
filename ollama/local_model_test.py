# a list of data consists of name, age, and city
db_data = {
    'Alice': {'age': 30, 'city': 'New York'},
    'Bob': {'age': 25, 'city': 'Los Angeles'},
    'Charlie': {'age': 35, 'city': 'Chicago'},
    'David': {'age': 28, 'city': 'Houston'},
    'Eve': {'age': 22, 'city': 'Phoenix'},
    'Frank': {'age': 40, 'city': 'Philadelphia'},
    'Grace': {'age': 27, 'city': 'San Antonio'},
    'Heidi': {'age': 32, 'city': 'San Diego'},
    'Ivan': {'age': 29, 'city': 'Dallas'},
    'Judy': {'age': 24, 'city': 'San Jose'}
}

from ollama import chat

# Prepare the database data as a string to send to the model
data_summary = "\n".join([
    f"{name}: Age {info['age']}, City {info['city']}" for name, info in db_data.items()
])

# We use the stream=True parameter to get an iterator back
stream = chat(
    model='deepseek-r1:8b',
    messages=[
        {
            'role': 'system',
            'content': "Here is the database of people: \n" + data_summary
        },
        {
            'role': 'user', 
            'content': "Who is the youngest person in the database, and which city are they from?"
        }
    ],
    stream=True,
)

print("--- DEEPSEEK R1 IS THINKING ---")

# Loop through the stream to print tokens as they arrive
for chunk in stream:
    # end='' ensures tokens stay on the same line
    # flush=True ensures the terminal updates immediately
    print(chunk.message.content, end='', flush=True)

print("\n--- DONE ---")