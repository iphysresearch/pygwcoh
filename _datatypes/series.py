"""
This is the module for gravitational wave coherent search.
Writer: Shallyn(shallyn.liu@foxmail.com)
"""

import numpy as np
from .._core import resample

class Series(object):
    def __init__(self, value, deltax, info = 'Series'):
        value = np.asarray(value)
        if (len(value.shape) != 1 and value.shape[0] != 1):
            raise Exception(f'Shape error: {value.shape}')
        self._value = value
        self._deltax = deltax
        self._info = info
    
    @property
    def value(self):
        return self._value
    
    @property
    def deltax(self):
        return self._deltax

    def __len__(self):
        return len(self._value)

    def __abs__(self):
        return abs(self._value)

    @property
    def size(self):
        return self._value.size
    
    @property
    def x(self):
        return np.arange(0, self.length, self._deltax)

    @property
    def length(self):
        return self._deltax * len(self)

    @property
    def real(self):
        return Series(self._value.real, self._deltax, info = f'Re_{self._info}')

    @property
    def imag(self):
        return Series(self._value.imag, self._deltax, info = f'Im_{self._info}')

    def conjugate(self):
        return Series(self._value.conjugate(), self._deltax, info = f'Conj_{self._info}')

    def __str__(self):
        return f'{self._info}: {self._value}'
    
    def __repr__(self):
        return self.__str__()
    
    def __format__(self):
        return self.__str__()
    
    def __iter__(self):
        for x in self._value:
            yield x

    def __getitem__(self, key):
        if isinstance(key, np.int):
            return self._value[key]
        return self._getslice(key)

    def _getslice(self, index):
        if isinstance(index, slice):        
            if index.start is not None and index.start < 0:
                raise ValueError(('Negative start index ({}) is not supported').format(index.start))
            
            if index.step is not None:
                new_deltax = self.deltax * index.step
            else:
                new_deltax = self.deltax
            return Series(self._value[index], deltax = new_deltax)
        if isinstance(index, np.ndarray):
            if len(index) == 1:
                return self._value[index]
            # Check uniform
            grad = np.gradient(index)
            if max(grad) != min(grad):
                raise ValueError(f'Invalid index for Series: {index}')
            step = index[1] - index[0]
            new_deltax = self._deltax * step
            return Series(self._value[index], deltax = new_deltax)

    
    def __setitem__(self, key, val):
        self._value[key] = val

    def resample(self, new_deltax):
        if new_deltax != self.deltax:
            new = resample(self.value, 1./self.deltax, 1./new_deltax)
            return Series(new, new_deltax, info = self._info)
        else:
            return self


class TimeSeries(Series):
    def __init__(self, value, epoch, fs, info = 'TimeSeries'):
        super(TimeSeries, self).__init__(value, 1./fs, info = info)
        self._epoch = epoch
    
    @property
    def fs(self):
        return int(1./self._deltax)
    
    @property
    def time(self):
        return self._epoch + self.x
    
    @property
    def epoch(self):
        return self._epoch
    
    def resample(self, fs_new):
        if fs_new != self.fs:
            new = resample(self.value, self.fs, fs_new)
            return TimeSeries(new, epoch=self.epoch, fs=self.fs, info=self.info)
        else:
            return self
    

class MultiSeries(object):
    def __init__(self, array, deltax, y):
        array = np.asarray(array)
        if len(array.shape) == 1:
            if array.shape[0] > 0:
                array = array.reshape(1, array.size)
                self._isempty = False
            else:
                array = np.array([])
                self._isempty = True
        self._array = array
        if not self._isempty:
            self._deltax = deltax
            if isinstance(y, np.int) or isinstance(y, np.float):
                y = [y]
            y = np.asarray(y)
            if len(y) > 0:
                if (len(y.shape) != 1 and y.shape[0] != 1):
                    raise Exception(f'Shape error for y: {y.shape}')
                if y.size != self._array.shape[0]:
                    raise Exception(f'Incompatible size for y: {y.size}')
                self._y = y.reshape(y.size)
            else:
                raise Exception(f'Invalid variable: {y}')
        else:
            self._deltax = None
            self._y = None

    @property
    def y(self):
        return self._y

    @property
    def deltax(self):
        return self._deltax

    @property
    def x(self):
        return np.arange(0, self.length, self._deltax)

    def __len__(self):
        return self.shape[1]

    @property
    def ysize(self):
        return self.shape[0]

    @property
    def length(self):
        return self.xsize * self._deltax
    
    @property
    def height(self):
        return self._y[-1] - self._y[0]

    @property
    def xsize(self):
        return self.shape[1]

    @property
    def shape(self):
        return self._array.shape

    def __iter__(self):
        for i in range(self.ysize):
            yield (self.y[i], Series(self._array[i,:], self.deltax))

    def append(self, series, y):
        if not isinstance(series, Series):
            series = Series(series, self.deltax)
        if not self._isempty:
            if len(series) != self.xsize:
                raise Exception(f'Incompatible size: {series.size} != {self.xsize}')
            if series.deltax != self.deltax:
                raise Exception(f'Incompatible deltax: {series.deltax} != {self.deltax}')
            if y > self._y[-1]:
                idx_insert = self.ysize
                self._array = np.insert(self._array, idx_insert, series.value, axis=0)
                self._y = np.insert(self._y, idx_insert, y)
            else:
                idx_insert = np.where(self._y - y >= 0)[0][0]
                if self._y[idx_insert] == y:
                    self._array[idx_insert,:] = series.value
                else:
                    self._array = np.insert(self._array, idx_insert, series.value, axis=0)
                    self._y = np.insert(self._y, idx_insert, y)
        else:
            size = series.size
            self._deltax = series.deltax
            self._array = series.value.reshape(1, size)
            if not isinstance(y, np.int) or not isinstance(y, np.float):
                raise TypeError(f'Invalid type: {type(y)}')
            self._y = np.array([y])


    
class TimeFreqSpectrum(MultiSeries):
    def __init__(self, array, epoch, fs, freqs, info = 'TimeFreqSpectrum'):
        super(TimeFreqSpectrum, self).__init__(array, 1./fs, freqs)
        if not self._isempty:
            if isinstance(epoch, np.int) or isinstance(epoch, np.float):
                epoch = [epoch]
            epoch = np.asarray(epoch)
            if len(epoch) == 1:
                self._epoch = np.ones(self.ysize) * epoch[0]
            elif len(epoch) == self.ysize:
                self._epoch = epoch
            else:
                raise Exception(f'Incompatible shape for epoch: {epoch.shape}')
        else:
            epoch = None
    @property
    def epoch(self):
        return self._epoch
    
    @property
    def fs(self):
        return 1./self.deltax
    
    @property
    def frequencies(self):
        return self.y

    def __iter__(self):
        for i in range(self.ysize):
            yield (self.frequencies[i], TimeSeries(self._array[i,:], self.epoch[i], self.fs, info = self._info))
        
    def append(self, timeseries, freq, epoch = None, fs = None):
        if not isinstance(timeseries, TimeSeries) and epoch is None:
            raise TypeError(f'Invalid type: {timeseries}')
        elif epoch is not None and isinstance(timeseries, np.ndarray):
            value = timeseries
            if fs is None:
                deltax = self.deltax
            else:
                deltax = fs
            size = value.size
        else:
            value = timeseries.value
            epoch = timeseries.epoch
            deltax = timeseries.deltax
            size = timeseries.size
            

        if not self._isempty:
            if size != self.xsize:
                raise Exception(f'Incompatible size: {timeseries.size} != {self.xsize}')
            if deltax != self.deltax:
                raise Exception(f'Incompatible deltax: {timeseries.deltax} != {self.deltax}')
            if freq > self._y[-1]:
                idx_insert = self.ysize
                self._array = np.insert(self._array, idx_insert, value, axis=0)
                self._epoch = np.insert(self._epoch, idx_insert, epoch)
                self._y = np.insert(self._y, idx_insert, freq)
            else:
                idx_insert = np.where(self._y - freq >= 0)[0][0]
                if self._y[idx_insert] == freq:
                    self._array[idx_insert, :] = value
                    self._epoch[idx_insert] = epoch
                else:
                    self._array = np.insert(self._array, idx_insert, value, axis=0)
                    self._epoch = np.insert(self._epoch, idx_insert, epoch)
                    self._y = np.insert(self._y, idx_insert, freq)
        else:
            self._array = value.reshape(1, size)
            self._epoch = np.array([epoch])
            self._y = np.array([freq])
            self._deltax = deltax



def CreateEmptySpectrum():
    array = np.array([])
    freqs = None
    epoch = None
    fs = 1
    empty = TimeFreqSpectrum(array, epoch, fs, freqs)
    return empty