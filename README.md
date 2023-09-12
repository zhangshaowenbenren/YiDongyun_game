# YiDongyun_game
单工况向多工况迁移学习的多分类问题（8个类别）
# 问题介绍
已知单工况下的有标签训练集dataset1，以及多工况下的无标签训练集dataset2，需要对多工况下的测试集进行分类。
# 总体思路：基于特征的迁移：利用单工况的数据进行迁移学习
#### 1.基于域适应迁移学习：MK-MMD （尝试过，效果不如方法2）
#### 2.动态对抗迁移学习DAAN（本文方法）
# 建模流程
## 0.数据预处理：将原始数据转化为图片
## 1. 用dataset1训练一个Resnet18，将特征提取器的参数初始化DAAN的参数。
  在train_first.py实现
  
  ResNet18包含特征提取器 + 分类器。

  DAAN包含特征提取器 + 分类器 + 域判别器。
## 2.进行动态对抗迁移学习模型的训练：
  在train.py实现
  #### 不仅希望源域特征分布和目标域特征分布相近；对应边缘分布P(X)
  #### 还希望相同类别下源域特征分布和目标域特征分布相近；对应条件分布P(X|Y)
  #### 当判别器无法区分源域特征和目标域特征时即认为相近
  ###### 损失函数 = 源域样本分类损失 + a * 边缘分布域判别损失 + (1 - a) * 条件分布域判别损失
  ###### 域判别器的输入为特征提取器的输出
  ###### 域判别器包含两类，一类用于对齐边缘分布（判断是源域还是目标域），一类用于对齐条件分布（8个域判别器）。
  ###### 条件分布的判别器用来计算P(X|Y),其中Y是分类器的预测结果。X是特征提取器的输出
  ##### 采用动态系数调节边缘分布损失项和条件分布损失项的权重

  训练数据：
单工况数据：8个类别，每个类别500个样本
多工况数据：2000个

测试数据：
多工况测试样本：2000个带标签样本

判别器包括边缘分布域判别器和条件分布域判别器。
边缘分布域判别器：用以判断当前输入数据是来自源域还是目标域
条件分布域判别器：在给定一个类别的前提下，判断当前输入数据是来自源域和目标域。


训练trick:
1. 先用单工况的数据预训练Resnet18（特征提取器）的参数。
2. 判别器的梯度在通过梯度法转层时，会乘以一个alpha，这个系数随着训练进行逐渐从0增加到1。
alpha=0时领域分类损失不会回传到编码器网络中，只有领域分类器得到训练；随着训练的进行， alpha逐渐增加，编码器得到训练，并开始逐步生成可以混淆领域分类器的特征。

3. 自适应的学习率下降策略
