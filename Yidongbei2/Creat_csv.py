# -*- coding:utf-8-*-

import pandas as pd
import os

def create_traincsv(data_dir, train_save):
    path_files = []
    labels = []
    for parent, _, files in os.walk(data_dir):
        for file in files:
            path_files.append(os.path.join(parent, file))
            labels.append(parent.split('\\')[-1])
    dic = {"data":path_files, 'label':labels}
    dic = pd.DataFrame(dic)
    dic.to_csv(train_save, index=False)


# 将训练集中有标签的8各类别的文件名合并到一个文件里，便于访问
if __name__=='__main__':
    # 训练集所在的文件夹
    train_dir = 'Row_data\\training\\labeled'
    # 输出的csv文件保存地址
    train_save = r'trian.csv'
    create_traincsv(train_dir, train_save)