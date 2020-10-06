import numpy as np


def to_categorical (y, num_classes=None, dtype='float32'):
	"""Converts a class vector (integers) to binary class matrix.

  E.g. for use with categorical_crossentropy.

  Arguments:
      y: class vector to be converted into a matrix
          (integers from 0 to num_classes).
      num_classes: total number of classes.
      dtype: The data type expected by the input. Default: `'float32'`.

  Returns:
      A binary matrix representation of the input. The classes axis is placed
      last.
  """
	y = np.array (y, dtype='int')
	input_shape = y.shape
	if input_shape and input_shape [-1] == 1 and len (input_shape) > 1:
		input_shape = tuple (input_shape [:-1])
	y = y.ravel ()
	if not num_classes:
		num_classes = np.max (y) + 1
	n = y.shape [0]
	categorical = np.zeros ((n, num_classes), dtype=dtype)
	categorical [np.arange (n), y] = 1
	output_shape = input_shape + (num_classes,)
	categorical = np.reshape (categorical, output_shape)
	return categorical
