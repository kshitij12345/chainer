import functools
import operator

import numpy
import pytest

import xchainer


@pytest.fixture
def inputs(request, shape_data, dtype_data):
    shape_tup = shape_data['tuple']
    dtype_name = dtype_data['name']
    return shape_tup, dtype_name


def _create_dummy_data(shape_tup, dtype, pattern=1):
    size = _size(shape_tup)
    if pattern == 1:
        if dtype == xchainer.Dtype.bool:
            return [i % 2 == 1 for i in range(size)]
        else:
            return [i for i in range(size)]
    else:
        if dtype == xchainer.Dtype.bool:
            return [i % 3 == 0 for i in range(size)]
        else:
            return [1 + i for i in range(size)]


def _create_dummy_ndarray(shape_tup, numpy_dtype):
    return numpy.arange(_size(shape_tup)).reshape(shape_tup).astype(numpy_dtype)


def _assert_array(array, expected_dtype, expected_shape, expected_total_size, expected_data_list):
    assert isinstance(array.dtype, xchainer.Dtype)
    assert isinstance(array.shape, xchainer.Shape)
    assert array.dtype == expected_dtype
    assert array.shape == expected_shape
    assert array.element_bytes == expected_dtype.itemsize
    assert array.total_size == expected_total_size
    assert array.total_bytes == expected_dtype.itemsize * expected_total_size
    assert array.debug_flat_data == expected_data_list
    assert array.is_contiguous
    assert array.offset == 0


def _assert_array_equals_ndarray(array, ndarray):
    assert array.shape == ndarray.shape
    assert array.total_size == ndarray.size
    assert array.ndim == ndarray.ndim
    assert array.element_bytes == ndarray.itemsize
    assert array.total_bytes == ndarray.itemsize * ndarray.size
    assert array.debug_flat_data == ndarray.ravel().tolist()
    assert array.is_contiguous == ndarray.flags['C_CONTIGUOUS']


def _assert_ndarray_equals_ndarray(ndarray1, ndarray2):
    assert ndarray1.shape == ndarray2.shape
    assert ndarray1.size == ndarray2.size
    assert ndarray1.ndim == ndarray2.ndim
    assert ndarray1.itemsize == ndarray2.itemsize
    assert ndarray1.strides == ndarray2.strides
    assert numpy.array_equal(ndarray1, ndarray2)
    assert ndarray1.dtype == ndarray2.dtype
    assert ndarray1.flags == ndarray2.flags


def _size(tup):
    return functools.reduce(operator.mul, tup, 1)


def test_init(inputs):
    shape_tup, dtype_name = inputs

    shape = xchainer.Shape(shape_tup)
    dtype = xchainer.Dtype(dtype_name)

    data_list = _create_dummy_data(shape_tup, dtype)

    array = xchainer.Array(shape, dtype, data_list)

    _assert_array(array, dtype, shape, _size(shape_tup), data_list)


def test_numpy_init(inputs):
    shape_tup, dtype_name = inputs

    shape = xchainer.Shape(shape_tup)
    dtype = xchainer.Dtype(dtype_name)

    numpy_dtype = getattr(numpy, dtype_name)

    ndarray = _create_dummy_ndarray(shape_tup, numpy_dtype)

    array = xchainer.Array(ndarray)

    _assert_array(array, dtype, shape, _size(shape_tup), ndarray.ravel().tolist())
    _assert_array_equals_ndarray(array, ndarray)

    # inplace modification
    if ndarray.size > 0:
        ndarray *= _create_dummy_ndarray(shape_tup, numpy_dtype)
        assert array.debug_flat_data == ndarray.ravel().tolist()

    _assert_array_equals_ndarray(array, ndarray)

    # test possibly freed memory
    data_copy = ndarray.copy()
    del ndarray
    assert array.debug_flat_data == data_copy.ravel().tolist()

    # recovered data should be equal
    data_recovered = numpy.array(array)
    _assert_ndarray_equals_ndarray(data_copy, data_recovered)

    # recovered data should be a copy
    data_recovered_to_modify = numpy.array(array)
    data_recovered_to_modify *= _create_dummy_ndarray(shape_tup, numpy_dtype)
    _assert_array_equals_ndarray(array, data_recovered)


def test_add_iadd(inputs):
    shape_tup, dtype_name = inputs

    shape = xchainer.Shape(shape_tup)
    dtype = xchainer.Dtype(dtype_name)

    lhs_data_list = _create_dummy_data(shape_tup, dtype, pattern=1)
    rhs_data_list = _create_dummy_data(shape_tup, dtype, pattern=2)

    lhs = xchainer.Array(shape, dtype, lhs_data_list)
    rhs = xchainer.Array(shape, dtype, rhs_data_list)

    expected_data_list = [x + y for x, y in zip(lhs_data_list, rhs_data_list)]
    if dtype == xchainer.Dtype.bool:
        expected_data_list = [x > 0 for x in expected_data_list]  # [0, 2] => [False, True]

    out = lhs + rhs
    assert out.debug_flat_data == expected_data_list
    assert lhs.debug_flat_data == lhs_data_list
    assert rhs.debug_flat_data == rhs_data_list

    lhs += rhs
    assert lhs.debug_flat_data == expected_data_list
    assert rhs.debug_flat_data == rhs_data_list


def test_mul_imul(inputs):
    shape_tup, dtype_name = inputs

    shape = xchainer.Shape(shape_tup)
    dtype = xchainer.Dtype(dtype_name)

    lhs_data_list = _create_dummy_data(shape_tup, dtype, pattern=1)
    rhs_data_list = _create_dummy_data(shape_tup, dtype, pattern=2)

    lhs = xchainer.Array(shape, dtype, lhs_data_list)
    rhs = xchainer.Array(shape, dtype, rhs_data_list)

    expected_data_list = [x * y for x, y in zip(lhs_data_list, rhs_data_list)]
    if dtype == xchainer.Dtype.bool:
        expected_data_list = [x > 0 for x in expected_data_list]  # [0, 1] => [False, True]

    out = lhs * rhs
    assert out.debug_flat_data == expected_data_list
    assert lhs.debug_flat_data == lhs_data_list
    assert rhs.debug_flat_data == rhs_data_list

    lhs *= rhs
    assert lhs.debug_flat_data == expected_data_list
    assert rhs.debug_flat_data == rhs_data_list


def test_array_init_invalid_length():
    with pytest.raises(xchainer.DimensionError):
        xchainer.Array((), xchainer.Dtype.int8, [])

    with pytest.raises(xchainer.DimensionError):
        xchainer.Array((), xchainer.Dtype.int8, [1, 1])

    with pytest.raises(xchainer.DimensionError):
        xchainer.Array((1,), xchainer.Dtype.int8, [])

    with pytest.raises(xchainer.DimensionError):
        xchainer.Array((1,), xchainer.Dtype.int8, [1, 1])

    with pytest.raises(xchainer.DimensionError):
        xchainer.Array((0,), xchainer.Dtype.int8, [1])

    with pytest.raises(xchainer.DimensionError):
        xchainer.Array((3, 2), xchainer.Dtype.int8, [1, 1, 1, 1, 1])

    with pytest.raises(xchainer.DimensionError):
        xchainer.Array((3, 2), xchainer.Dtype.int8, [1, 1, 1, 1, 1, 1, 1])
