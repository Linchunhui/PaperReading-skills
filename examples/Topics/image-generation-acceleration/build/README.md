构建增订版需要原稿目录、其原图和topic.json，以及已有本地论文PDF。原稿不作修改。

安装 beautifulsoup4、pymupdf、pillow 后执行：

```sh
python build_public.py --source /path/to/original --corpus /path/to/pdfs --output /path/to/new-output
```

research-summary.json、NOTICE.md与benchmark-template.csv为独立发布记录；构建后保留这些文件。原图还须按清单逐张目视核对。
