# 能量丢失检测程序 #
## 依赖的库 ##
FFTW3 <http://www.fftw.org>

libsndfile <https://github.com/erikd/libsndfile>

## 编译 ##
	gcc -o lossenergy lossenergy.c window.c spectrum.c common.c -I/usr/local/include -L/usr/local/lib -lfftw3 -lsndfile 
	
## andriod编译 ##
### 编译依赖库libsndfile ###
SNDFILE Building for Android <https://github.com/erikd/libsndfile/blob/master/Building-for-Android.md>

**注意ndk 15c以后的版本均无法通过，一部分不支持c99的命令格式，18以后版本连gcc都没有了。**

```
ANDROID_NDK_VER=${ANDROID_NDK_VER:-r15c}
ANDROID_GCC_VER=${ANDROID_GCC_VER:-4.9}
ANDROID_API_VER=${ANDROID_API_VER:-16}
ANDROID_TARGET=${ANDROID_TARGET:-arm-linux-androideabi}
```
### 编译依赖库fftw3 ###
fftw3 Building for Android <https://github.com/Lauszus/fftw3-android/>

**注意这个版本中的fftw3是3.3.5，不兼容，需要去下载3.3.8 <http://www.fftw.org/fftw-3.3.8.tar.gz>。用新的软件覆盖掉其中fftw3目录，但要注意不要替换掉Android.mk和config.h就可以通过它的介绍来编译了**

### 通过ndk编译成.so ###
**Andriod.mk**

```
LOCAL_PATH := $(call my-dir)
include $(CLEAR_VARS)
LOCAL_MODULE := fftw3
LOCAL_SRC_FILES := $(LOCAL_PATH)/lossenergy/lib/libfftw3.a 
LOCAL_EXPORT_C_INCLUDES := $(LOCAL_PATH)/lossenergy/include
include $(PREBUILT_STATIC_LIBRARY)

include $(CLEAR_VARS)
LOCAL_MODULE := sndfile
LOCAL_SRC_FILES := $(LOCAL_PATH)/lossenergy/lib/libsndfile.a
LOCAL_EXPORT_C_INCLUDES := $(LOCAL_PATH)/lossenergy/include
include $(PREBUILT_STATIC_LIBRARY)

include $(CLEAR_VARS)
LOCAL_MODULE     := lossenergy
LOCAL_SRC_FILES  := lossenergy/spectrogram.c lossenergy/common.c lossenergy/spectrum.c lossenergy/window.c
LOCAL_CFLAGS := -std=c99
LOCAL_C_INCLUDES:= $(LOCAL_PATH)/lossenergy/include
LOCAL_LDLIBS :+= -llog -lm
LOCAL_STATIC_LIBRARIES :=  fftw3  sndfile 
include $(BUILD_SHARED_LIBRARY)

```


**Application.mk**

```
APP_ABI := armeabi armeabi-v7a
APP_PLATFORM := android-16
APP_STL := stlport_static
APP_CPPFLAGS += -fexceptions
APP_CPPFLAGS +=-std=c++11
STLPORT_FORCE_REBUILD := true
```