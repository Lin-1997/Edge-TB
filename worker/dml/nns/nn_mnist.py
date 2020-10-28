from tensorflow.keras import Input, layers, Model, losses


class Mnist (object):
	def __init__ (self):
		self.input_shape = [-1, 28 * 28]  # -1 means no matter how much data

		inputs = Input (shape=tuple (self.input_shape) [1:])
		x = layers.Dense (512, activation='sigmoid') (inputs)
		x = layers.Dense (256, activation='sigmoid') (x)
		x = layers.Dense (128, activation='sigmoid') (x)
		outputs = layers.Dense (10) (x)

		self.model = Model (inputs, outputs)
		self.model.compile (optimizer='adam', loss=losses.SparseCategoricalCrossentropy (from_logits=True),
			metrics=['accuracy'])

		self.size = 4 * self.model.count_params ()  # 4 byte per np.float32


nn = Mnist ()
