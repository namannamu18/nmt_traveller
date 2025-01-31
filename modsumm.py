#NMT Model Code
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
from tensorflow.keras.models import load_model # type: ignore

# Load the model from .h5 file
model = load_model("nmt_model.h5")

# Display the model summary
model.summary()
