from cryptoscope.extract.raw_extractor import RawExtractor
from cryptoscope.transform.data_transformer import DataTransformer
from cryptoscope.validate.candle_validator import CandleValidator


class CryptoScopePipeline:
    def __init__(self):
        self.extractor = RawExtractor()
        self.transformer = DataTransformer()
        self.validator = CandleValidator()

    def run(self):
        try:
            raw_data = self.extractor.run()
            tables = self.transformer.run(raw_data)
            clean_tables, rejected_tables = self.validator.run(tables)

            # Next: self.loader.run(clean_tables, rejected_tables)

            print(f"Pipeline finished. Coins validated: {len(clean_tables)}")

        except Exception as e:
            print("Pipeline failed:", e)


if __name__ == "__main__":
    CryptoScopePipeline().run()