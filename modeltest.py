#NMT Model Code
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
from tensorflow.keras.models import Model # type: ignore
from flask import Flask, render_template, request, jsonify
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model

app = Flask(__name__)

# Load the trained model
model = load_model("nmt_model.h5")
encoder_model = model.get_layer(index=0)
decoder_model = model.get_layer(index=1)

# Load token indices
input_token_index = {}  # Populate with actual input character indices
target_token_index = {}  # Populate with actual target character indices
reverse_target_char_index = {i: char for char, i in target_token_index.items()}

max_decoder_seq_length = 100  # Adjust based on trained model
num_decoder_tokens = len(target_token_index)

@app.route('/')
def index():
    return render_template('index.html')

def decode_sequence(input_seq):
    states_value = encoder_model.predict(input_seq)
    target_seq = np.zeros((1, 1, num_decoder_tokens))
    target_seq[0, 0, target_token_index['\t']] = 1.
    decoded_sentence = ''
    stop_condition = False
    
    while not stop_condition:
        output_tokens, h, c = decoder_model.predict([target_seq] + states_value)
        sampled_token_index = np.argmax(output_tokens[0, -1, :])
        sampled_char = reverse_target_char_index[sampled_token_index]
        decoded_sentence += sampled_char

        if sampled_char == '\n' or len(decoded_sentence) > max_decoder_seq_length:
            stop_condition = True

        target_seq = np.zeros((1, 1, num_decoder_tokens))
        target_seq[0, 0, sampled_token_index] = 1.
        states_value = [h, c]
    
    return decoded_sentence

@app.route('/translate', methods=['POST'])
def translate():
    input_text = request.form['input_text']
    input_seq = np.zeros((1, len(input_text), len(input_token_index)))
    for t, char in enumerate(input_text):
        input_seq[0, t, input_token_index.get(char, 0)] = 1.
    translated_text = decode_sequence(input_seq)
    return jsonify({'translated_text': translated_text})

if __name__ == '__main__':
    app.run(debug=True)
