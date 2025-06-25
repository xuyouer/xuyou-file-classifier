# xuyou-file-classifier

这是一个自动将文件按类型分类到对应文件夹的小工具

项目背景: 原有的某个💩项目，需要将文件分门别类，灵光一现，它灵光一现了

## Github

[https://github.com/xuyouer/xuyou-file-classifier](https://github.com/xuyouer/xuyou-file-classifier)

## 软件截图

![软件截图](images/xuyou-file-classifier.png)

## TODO

- ✅ 可自选输出分类路径(默认路径: **f"./{日期+唯一ID}分类"**)
- ✅ 分类完成后，继续分类将排除输出分类路径，防止二次重复
- ✅ 可选分类时是否保持原有的子目录结构
- ✅ 可选分类后是否保留原有的文件夹(未成功分类的除外)
- 🔲 ~~分类规则存放云端(Github/……)，本地可联网下载使用(视情况决定后续版本是否更新此内容)~~

## TIPS

**注意**

1. 内置的默认分类规则可能部分不符(直接使用的百度搜索结果)，如有不符或需要扩展内置请指出，感谢

## 版本日志

### v1.0.1

更新 [FEAT]:

1. 所有设置存放SettingsManager进行管理
2. 部分功能

修复 [FIX]:

1. 部分不合理的分类规则

### v1.0.0

## 贡献

欢迎提交[Issue](https://github.com/xuyouer/xuyou-file-classifier/issues)
和[Pull Request](https://github.com/xuyouer/xuyou-file-classifier/pulls)来帮助改进这个工具。

## 许可证

本项目采用MIT许可证 - 详见[LICENSE](https://github.com/xuyouer/xuyou-file-classifier/blob/main/LICENSE)文件。