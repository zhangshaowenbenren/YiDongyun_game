# -*- coding:utf-8-*-

import torch
import torch.nn as nn
from BaseModel import Resnet18
from torch.autograd import Function
from torch.nn import functional as F

class ReverseLayerF(Function):
    @staticmethod                   # 静态方法，不可以引用类的属性和方法；也不需要self参数
    def forward(ctx, x, alpha):
        ctx.alpha = alpha

        return x.view_as(x)

    @staticmethod
    def backward(ctx, grad_output):
        output = grad_output.neg() * ctx.alpha
        return output, None


class Residual(nn.Module):   #@save
    def __init__(self, input_channels=1, mid_channels=32, num_channels=1, use_1x1conv=False, strides=1):
        super().__init__()
        self.conv1 = nn.Conv1d(input_channels, mid_channels,
        kernel_size=5, padding=2, stride=strides)
        self.conv2 = nn.Conv1d(mid_channels, num_channels,
        kernel_size=5, padding=2)
        if use_1x1conv:
            self.conv3 = nn.Conv1d(input_channels, num_channels,
            kernel_size=1, stride=strides)
        else:
            self.conv3 = None
        self.bn1 = nn.BatchNorm1d(mid_channels)
        self.bn2 = nn.BatchNorm1d(num_channels)
        self.relu = nn.ReLU(inplace=True)


    def forward(self, X):
        Y = F.relu(self.bn1(self.conv1(X)))
        Y = self.bn2(self.conv2(Y))
        if self.conv3:
            X = self.conv3(X)
            Y += X
        return F.relu(Y)


class DANNet(nn.Module):
    def __init__(self, num_classes=8):
        super(DANNet, self).__init__()
        self.sharedNet =  Resnet18()
        # 瓶颈层用于特征迁移
        self.bottleneck = nn.Sequential(nn.Linear(512, 256),
                                        nn.BatchNorm1d(256),
                                        nn.ReLU(),
                                        nn.Linear(256, 128),
                                        nn.BatchNorm1d(128),
                                        nn.ReLU()
                                        )
        # 分类层，用于类别分类
        self.source_fc = nn.Sequential(nn.Linear(128, num_classes), nn.LogSoftmax())
        self.softmax = nn.Softmax(dim=1)
        self.classes = num_classes

        #全局域判别器
        self.domain_classifier = nn.Sequential()
        self.domain_classifier.add_module('fc1', nn.Linear(512, 1024))
        self.domain_classifier.add_module('bn1', nn.BatchNorm1d(1024))
        self.domain_classifier.add_module('relu1', nn.ReLU())
        self.domain_classifier.add_module('drop1', nn.Dropout())
        self.domain_classifier.add_module('fc2', nn.Linear(1024,1024))
        self.domain_classifier.add_module('bn2', nn.BatchNorm1d(1024))
        self.domain_classifier.add_module('relu2', nn.ReLU())
        self.domain_classifier.add_module('drop2', nn.Dropout())
        self.domain_classifier.add_module('fc3',nn.Linear(1024, 512))
        self.domain_classifier.add_module('bn3', nn.BatchNorm1d(512))
        self.domain_classifier.add_module('relu3',nn.ReLU())
        self.domain_classifier.add_module('drop3',nn.Dropout())
        self.domain_classifier.add_module('fc4', nn.Linear(512, 2))
        self.domain_classifier.add_module('d_softmax', nn.LogSoftmax())
        self.dcis = nn.Sequential()
        self.dci = {}
        # 添加不同类别的条件分布的领域判别器
        for i in range(num_classes):
            self.dci[i] = nn.Sequential()
            self.dci[i].add_module('fc1', nn.Linear(512, 1024))
            self.dci[i].add_module('bn1', nn.LayerNorm(1024))
            self.dci[i].add_module('relu1', nn.ReLU())
            self.dci[i].add_module('dpt1', nn.Dropout())
            self.dci[i].add_module('fc2', nn.Linear(1024, 1024))
            self.dci[i].add_module('bn2', nn.LayerNorm(1024))
            self.dci[i].add_module('relu2', nn.ReLU())
            self.dci[i].add_module('dpt2', nn.Dropout())
            self.dci[i].add_module('fc3', nn.Linear(1024, 512))
            self.dci[i].add_module('bn3', nn.LayerNorm(512))
            self.dci[i].add_module('relu3', nn.ReLU())
            self.dci[i].add_module('dpt3', nn.Dropout())
            self.dci[i].add_module('fc4', nn.Linear(512, 2))
            self.dci[i].add_module('d_softmax', nn.LogSoftmax())
            self.dcis.add_module('dci_' + str(i), self.dci[i])


    def forward(self, source, alpha=0.0):
        source_share = self.sharedNet(source)
        source = self.bottleneck(source_share)      # 特征提取器的输出, 用以计算MK-MMD
        source = self.source_fc(source)             # 分类器的输出
        source_label = source.data.max(1)[1]
        sout = torch.tensor([]).to('cuda')
        s_reverse_feature = ReverseLayerF.apply(source_share, alpha)
        s_domain_clf = self.domain_classifier(s_reverse_feature)     # 源域和目标域的判别损失（边缘分布）
        for k, i in enumerate(source_label):
            index = int(i.cpu().detach().numpy())
            sout = torch.cat([sout, self.dcis[index](s_reverse_feature[k].unsqueeze(0))],dim=0)    # 条件分布
        return source, s_domain_clf, sout, source_share


    def predict(self,x):
        x = self.sharedNet(x)
        x = self.bottleneck(x)
        x = self.source_fc(x)
        return x


if __name__=='__main__':
    res = Residual()
    data = torch.randn(32, 1, 512)
    lin = nn.Linear(512, 1024)
    flat = nn.Flatten()
    print(flat(lin(res(data))).shape)