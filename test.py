#NMT Model Code
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
from tensorflow.keras.models import Model # type: ignore
from tensorflow.keras.layers import Input, LSTM, Dense # type: ignore
import numpy as np
import tensorflow as tf
#import tf2onnx

batch_size=64
epochs=100
latent_dim=256
num_samples=10000
data_path='kan-eng/kan.txt'

#vectorize the data
input_texts=[]
target_texts=[]
input_characters=set()
target_characters=set()

with open(data_path,'r',encoding='utf-8') as f:
    lines=f.read().split('\n')
for line in lines[:min(num_samples,len(lines)-1)]:
    input_text,target_text,_=line.split('\t')

    target_text='\t'+target_text+'\n'
    input_texts.append(input_text)
    target_texts.append(target_text)
    for char in input_text:
        if char not in input_characters:
            input_characters.add(char)
    for char in target_text:
        if char not in target_characters:
            target_characters.add(char)

#print(input_characters)
#print(target_characters)

input_characters=sorted(list(input_characters))
target_characters=sorted(list(target_characters))
num_encoder_tokens=len(input_characters)
num_decoder_tokens=len(target_characters)
max_encoder_seq_length=max([len(txt) for txt in input_texts])
max_decoder_seq_length=max([len(txt) for txt in target_texts])

print('Number of samples:',len(input_texts))
print('Number of unique input tokens:',num_encoder_tokens)
print('Number of unique output tokens:',num_decoder_tokens)
print('Max sequence length for inputs:',max_encoder_seq_length)
print('Max sequence length for outputs:',max_decoder_seq_length)

input_token_index=dict(
    [(char,i) for i, char in enumerate(input_characters)]
)
target_token_index=dict(
    [(char,i) for i, char in enumerate(target_characters)]
)

#print(input_token_index,target_token_index)
encoder_input_data=np.zeros(
    (len(input_texts),max_encoder_seq_length,num_encoder_tokens),dtype='float32'
)
decoder_input_data=np.zeros(
    (len(input_texts),max_decoder_seq_length,num_decoder_tokens),dtype='float32'
)
decoder_target_data=np.zeros(
    (len(input_texts),max_decoder_seq_length,num_decoder_tokens),dtype='float32'
)

for i, (input_text,target_text) in enumerate(zip(input_texts,target_texts)):
    for t,char in enumerate(input_text):
        encoder_input_data[i,t,input_token_index[char]]=1.
    encoder_input_data[i,t+1:,input_token_index[' ']]=1.
    for t, char in enumerate(target_text):
        decoder_input_data[i,t,target_token_index[char]]=1.
        if t>0:
            decoder_target_data[i,t-1,target_token_index[char]]=1.
    decoder_input_data[i,t+1:,target_token_index[' ']]=1.
    decoder_target_data[i,t:,target_token_index[' ']]=1. 


encoder_inputs = Input(shape=(None, num_encoder_tokens))
encoder = LSTM(latent_dim, return_state=True)
encoder_outputs, state_h, state_c = encoder(encoder_inputs)
# We discard `encoder_outputs` and only keep the states.
encoder_states = [state_h, state_c]

# Set up the decoder, using `encoder_states` as initial state.
decoder_inputs = Input(shape=(None, num_decoder_tokens))
# We set up our decoder to return full output sequences,
# and to return internal states as well. We don't use the 
# return states in the training model, but we will use them in inference.
decoder_lstm = LSTM(latent_dim, return_sequences=True, return_state=True)
decoder_outputs, _, _ = decoder_lstm(decoder_inputs,
                                     initial_state=encoder_states)
decoder_dense = Dense(num_decoder_tokens, activation='softmax')
decoder_outputs = decoder_dense(decoder_outputs)

# Define the model that will turn
# `encoder_input_data` & `decoder_input_data` into `decoder_target_data`
model = Model([encoder_inputs, decoder_inputs], decoder_outputs)

# Run training
model.compile(optimizer='rmsprop', loss='categorical_crossentropy')
model.fit([encoder_input_data, decoder_input_data], decoder_target_data,
          batch_size=batch_size,
          epochs=epochs,
          validation_split=0.2)
encoder_model = Model(encoder_inputs, encoder_states)

decoder_state_input_h = Input(shape=(latent_dim,))
decoder_state_input_c = Input(shape=(latent_dim,))
decoder_states_inputs = [decoder_state_input_h, decoder_state_input_c]
decoder_outputs, state_h, state_c = decoder_lstm(
    decoder_inputs, initial_state=decoder_states_inputs)
decoder_states = [state_h, state_c]
decoder_outputs = decoder_dense(decoder_outputs)
decoder_model = Model(
    [decoder_inputs] + decoder_states_inputs,
    [decoder_outputs] + decoder_states)

reverse_input_char_index=dict(
    (i,char) for char, i in input_token_index.items())
reverse_target_char_index=dict(
    (i,char) for char, i in target_token_index.items())

# Save the model in .h5 format
model.save("nmt_model.h5")
print("Model saved as nmt_model.h5")

# Convert to ONNX format
onnx_model_path = "nmt_model.onnx"
spec = (tf.TensorSpec(model.input_shape[0], tf.float32), tf.TensorSpec(model.input_shape[1], tf.float32))

# Use the tf2onnx API
"""model_proto, _ = tf2onnx.convert.from_keras(model, input_signature=spec, opset=13)
with open(onnx_model_path, "wb") as f:
    f.write(model_proto.SerializeToString())"""

print(f"Model saved as {onnx_model_path}")



def decode_sequence(input_seq):
    # Encode the input as state vectors.
    states_value = encoder_model.predict(input_seq)

    # Generate empty target sequence of length 1.
    target_seq = np.zeros((1, 1, num_decoder_tokens))
    # Populate the first character of target sequence with the start character.
    target_seq[0, 0, target_token_index['\t']] = 1.

    # Sampling loop for a batch of sequences
    # (to simplify, here we assume a batch of size 1).
    stop_condition = False
    decoded_sentence = ''
    while not stop_condition:
        output_tokens, h, c = decoder_model.predict(
            [target_seq] + states_value)

        # Sample a token
        sampled_token_index = np.argmax(output_tokens[0, -1, :])
        sampled_char = reverse_target_char_index[sampled_token_index]
        decoded_sentence += sampled_char

        # Exit condition: either hit max length
        # or find stop character.
        if (sampled_char == '\n' or
           len(decoded_sentence) > max_decoder_seq_length):
            stop_condition = True

        # Update the target sequence (of length 1).
        target_seq = np.zeros((1, 1, num_decoder_tokens))
        target_seq[0, 0, sampled_token_index] = 1.

        # Update states
        states_value = [h, c]

    return decoded_sentence
