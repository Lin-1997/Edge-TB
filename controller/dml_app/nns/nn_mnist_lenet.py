from tensorflow.keras import Input, layers, Model, losses


class Mnist (object):
	def __init__ (self):
		self.input_shape = [-1, 28, 28, 1]  # -1 means no matter how much data

		inputs = Input (shape=tuple (self.input_shape) [1:])
		x = layers.Conv2D (6, (5, 5), padding='same', activation='relu') (inputs)
		x = layers.MaxPooling2D ((2, 2)) (x)
		x = layers.Conv2D (16, (5, 5), padding='same', activation='relu') (x)
		x = layers.MaxPooling2D ((2, 2)) (x)
		x = layers.Flatten () (x)
		x = layers.Dense (120, activation='relu') (x)
		x = layers.Dense (84, activation='relu') (x)
		outputs = layers.Dense (10) (x)

		self.model = Model (inputs, outputs)
		self.model.compile (optimizer='adam', loss=losses.SparseCategoricalCrossentropy (from_logits=True),
			metrics=['accuracy'])

		self.size = 4 * self.model.count_params ()  # 4 byte per np.float32


nn = Mnist ()
