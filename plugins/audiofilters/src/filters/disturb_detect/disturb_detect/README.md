# 干扰音检测程序 #
## 依赖的库 ##
FFTW3 <http://www.fftw.org>

libsndfile <https://github.com/erikd/libsndfile>

## 编译 ##
	gcc -o disturb-detect spectrogram.c window.c spectrum.c common.c -I/usr/local/include -L/usr/local/lib -lfftw3 -lsndfile 
	
## andriod编译 ##

参考能量丢失项目

## 检测过程 ##
**检测前0.5秒静音段，由于需要检查每个频点X每个采样点（共8000个），计算量较大，速度较慢，可以仅用于环境检测段的检测，或者前几句的检测。可以通过FRAME_DETECT预编译变量来调整检查的采样点数量，不过调整了这个后，后续**

**一共分了4000个频点进行检测。**

**检测分为两种**

* 稳定的干扰。针对每个频点，如果在8000个采样点上的平均能量大于0.15，而且他们的方差/平均能量 <8%，说明这个频点上能量有且持续，可能是干扰。
* 较大的不稳定的干扰。针对在8000个采样点上的平均能量值大于1，但不考虑他们的方差，说明这个频点可能有问题。

## 输出和返回 ##
**输出样例:**

```
for file in OK/*; do    echo -n $file "";    ./disturb-detect $file ; done
for file in ERROR/*; do    echo -n $file "";    ./disturb-detect $file ; done
稳定干扰音频段数:0	能量集中频段数:2	检测到2个干扰音频段
稳定干扰音频段数:0	能量集中频段数:5	检测到5个干扰音频段
稳定干扰音频段数:0	能量集中频段数:2	检测到2个干扰音频段
稳定干扰音频段数:0	能量集中频段数:5	检测到5个干扰音频段
稳定干扰音频段数:0	能量集中频段数:7	检测到7个干扰音频段
稳定干扰音频段数:0	能量集中频段数:9	检测到9个干扰音频段
稳定干扰音频段数:0	能量集中频段数:0	检测通过
稳定干扰音频段数:0	能量集中频段数:0	检测通过
稳定干扰音频段数:0	能量集中频段数:0	检测通过
稳定干扰音频段数:0	能量集中频段数:0	检测通过
稳定干扰音频段数:0	能量集中频段数:0	检测通过
稳定干扰音频段数:0	能量集中频段数:0	检测通过
```
**返回值：以上两种频点数的合计**

##测试效果##
```
for file in ERROR/*; do    echo -n $file "";    ./disturb-detect $file ; done >error.txt

for file in OK/*; do    echo -n $file "";    ./disturb-detect $file ; done >ok.txt
```
ok.txt	总数618	错误数18

error.txt	总数600	错误数64
