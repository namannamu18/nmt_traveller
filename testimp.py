#NMT Model Code
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
from test import decode_sequence

print(decode_sequence("how are you"))