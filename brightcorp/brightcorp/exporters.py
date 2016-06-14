from scrapy.contrib.exporter import JsonLinesItemExporter
from scrapy.utils.serialize import ScrapyJSONEncoder

class BrightcorpItemExporter(JsonLinesItemExporter):

    def __init__(self, file, **kwargs):
        super(BrightcorpItemExporter, self).__init__(file, **kwargs)
        self.encoder = ScrapyJSONEncoder(ensure_ascii=False, **kwargs)