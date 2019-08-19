### 噪音检测API
本模块主要是采用sox工具利用分贝噪音检测和能量噪声检测相结合的方法，对语音进行检测，并对噪声类型进行了分类，主要包含：
直流偏移，持续底噪，高频丢失等类别。由于API功能有限，有些音频需要人工质检。
语音要求：
此程序对语音格式有一定的要求，要求为pcm编码格式的16位，16k采样频率的WAV格式的音频文件。

#### sox安装
1. linux
` apt-get insatll sox`
2. windows
下载 [sox](<https://sourceforge.net/projects/sox/files/sox/>)，并将其安装到checknoise目录下

#### 标签种类：
   normal：正常
   DC offset：直流偏移
   continue noise：其他
   high frequency loss: 高频丢失
   need manual detect：需要人工质检
   audio damage：音频损坏

#### 注意事项
程序运行过程中可能会有如下提示：
`WARN sinc: sinc clipped 7 samples; decrease volume?`
`WARN dither: dither clipped 1 samples; decrease volume?`
请忽略即可。