from tensorflow.keras import Input, layers, Model, losses


class FashionMnist (object):
	def __init__ (self):
		self.input_shape = [-1, 28, 28, 1]  # -1 means no matter how much data

		# Block 1
		inputs = Input (shape=tuple (self.input_shape) [1:])
		x = layers.Conv2D (32, (3, 3), padding='same', activation='relu') (inputs)
		x = layers.BatchNormalization () (x)
		x = layers.Conv2D (32, (3, 3), padding='same', activation='relu') (x)
		x = layers.BatchNormalization () (x)
		x = layers.MaxPooling2D ((2, 2)) (x)
		# Block 2
		x = layers.Conv2D (64, (3, 3), padding='same', activation='relu') (x)
		x = layers.BatchNormalization () (x)
		x = layers.MaxPooling2D ((2, 2)) (x)
		# Classification block
		x = layers.Flatten () (x)
		x = layers.Dense (64, activation='relu') (x)
		outputs = layers.Dense (10) (x)

		self.model = Model (inputs, outputs)
		self.model.compile (optimizer='adam', loss=losses.SparseCategoricalCrossentropy (from_logits=True),
			metrics=['accuracy'])

		self.size = 4 * self.model.count_params ()  # 4 byte per np.float32


nn = FashionMnist ()
