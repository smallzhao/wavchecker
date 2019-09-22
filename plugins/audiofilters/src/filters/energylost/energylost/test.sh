#!/bin/bash
function getdir(){
    for element in `ls $1`
    do  
        dir_or_file=$1"/"$element
        if [ -d $dir_or_file ]
        then 
            getdir $dir_or_file
        else
            if [ "${dir_or_file#*.}" == "wav" ]
            then
                echo $dir_or_file `/Users/datatang/code/lossenergy/lossenergy $dir_or_file `
            fi
        fi  
    done
}
root_dir="/Volumes/数据处理中心内部使用/语谱图测试"
getdir $root_dir