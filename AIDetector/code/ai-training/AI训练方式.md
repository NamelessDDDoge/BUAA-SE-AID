# AI模型训练与评测方式

## 训练启动

```shell
python train.py
```

## 批量评测启动

```shell
python eval.py
```

## 单图推理启动

```shell
python infer.py
```

## 主要参数调节方式

### 训练数据

在`data`文件夹内创建一个名为`***.txt`的文件，并在`configs/coarse_bio_hyper_para.py`中将`hp["data"]["train"]`设为前面的`***`，即可使用该数据训练

将`hp["data"]["test"]`设为对应的txt文件名，即可使用该数据评测



txt文件内的内容组成为：很多行的`图片路径 mask图片路径 是否为造假图片`，每一行为一条数据