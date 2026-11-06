from cryptoscope.extract.raw_extractor import RawExtractor
from cryptoscope.transform.data_transformer import DataTransformer
from cryptoscope.validate.candle_validator import CandleValidator
from cryptoscope.load.load_stage import LoadStage


class CryptoScopePipeline:
    def __init__(self):
        self.extractor = RawExtractor()
        self.transformer = DataTransformer()
        self.validator = CandleValidator()
        self.loader = LoadStage()

    def run(self):
        try:
            raw_data = self.extractor.run()
            tables = self.transformer.run(raw_data)
            clean_tables, rejected_tables, reports = self.validator.run(tables)
            run_id = self.loader.run(clean_tables, rejected_tables, reports)

            print(f"Pipeline finished. Run id: {run_id}")

        except Exception as e:
            print("Pipeline failed:", e)


if __name__ == "__main__":
    CryptoScopePipeline().run()