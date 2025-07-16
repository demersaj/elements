import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path

import markdownify
from bs4 import BeautifulSoup
from caseconverter import kebabcase
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
)
from docling_core.types.doc import (
    ImageRefMode,
    PictureItem,
    TableItem,
    TextItem,
)
from docling_core.types.doc.labels import DocItemLabel


class OCR:
    def __init__(
        self,
        res: float = 2.0,  # TODO: Dynamic for us
        input_path: Path = None,  # file path
        output_path: Path = None,
    ):
        self.res = res
        self.input_path = input_path
        self.output_path = output_path

    def _extract_tags(self, html_content):
        soup = BeautifulSoup(html_content, "html.parser")
        figures = soup.find_all("figure")
        tables = soup.find_all("table")

        figure_data = []
        table_data = []
        for figure in figures:
            caption = figure.find("figcaption")

            if caption:
                figure_data.append({"caption": caption.text})

            elif not caption:
                figure_data.append({"caption": ""})

        for table in tables:
            caption = table.find("caption")
            content = table.find("tbody")

            if caption and table:
                table_data.append({"caption": caption.text, "table_content": content})

            elif not caption and table:
                table_data.append({"caption": "", "table_content": content})

        return figure_data, table_data

    def extract(self):
        _log = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

        # TODO: read and process more file types - docx, png, ....
        pipeline_options = PdfPipelineOptions()
        pipeline_options.images_scale = self.res
        pipeline_options.generate_page_images = True
        pipeline_options.generate_picture_images = True

        doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        DEFAULT_EXPORT_LABELS = {
            DocItemLabel.TITLE,
            DocItemLabel.DOCUMENT_INDEX,
            DocItemLabel.SECTION_HEADER,
            DocItemLabel.PARAGRAPH,
            # DocItemLabel.TABLE,
            DocItemLabel.PICTURE,
            DocItemLabel.FORMULA,
            DocItemLabel.CHECKBOX_UNSELECTED,
            DocItemLabel.CHECKBOX_SELECTED,
            DocItemLabel.TEXT,
            DocItemLabel.LIST_ITEM,
            DocItemLabel.CODE,
            DocItemLabel.REFERENCE,
            DocItemLabel.PAGE_HEADER,
            DocItemLabel.PAGE_FOOTER,
        }

        start_time = time.time()

        _log.info(f"Processing file: {self.input_path}")
        conv_res = doc_converter.convert(self.input_path)

        doc_filename = kebabcase(str(conv_res.input.file.stem))
        image_outpath = (
            self.output_path
            / kebabcase(Path(self.input_path).stem)
            / f"{kebabcase(Path(self.input_path).stem)}_artifacts"
        )

        picture_res = conv_res.document._with_pictures_refs(image_outpath)

        output_dir = self.output_path / doc_filename
        output_dir.mkdir(parents=True, exist_ok=True)

        table_dir = output_dir / "tables"
        table_dir.mkdir(parents=True, exist_ok=True)

        # TODO: formula extraction and appending correctly to md file

        page_texts = {}
        page_images = {}
        page_tables = {}

        table_counter = 0
        for element, _level in conv_res.document.iterate_items():
            page_number = element.prov[0].page_no if element.prov else ""

            if page_number not in page_texts and isinstance(page_number, int):
                page_texts[int(page_number)] = []

            if isinstance(element, TextItem):
                if isinstance(page_number, int):
                    if page_number not in page_texts:
                        page_texts[page_number] = []
                    page_texts[page_number].append(element.text.strip())

            elif isinstance(element, TableItem):
                if self.input_path.suffix == ".pdf":
                    table_counter += 1
                    element_image_filename = table_dir / f"table-{table_counter}.png"
                    with element_image_filename.open("wb") as fp:
                        element.get_image(conv_res.document).save(fp, "PNG")

                # table_html = element.export_to_html(doc=conv_res.document)
                # _, table_data = self._extract_tags(table_html)
                # table_md = markdownify.markdownify(
                #    f"<table>{table_data[0]['table_content']}</table>",
                #    heading_style="ATX",
                # )
                table_md = element.export_to_markdown()

                page_tables[table_md] = {
                    "page_number": (
                        int(page_number) if page_number != "" else page_number
                    ),
                    "caption": "",
                }

        for page in page_texts.keys():
            content_list = page_texts[page]
            page_texts[page] = " ".join(content_list)

        for element, _level in picture_res.iterate_items():
            if isinstance(element, PictureItem):
                page_number = element.prov[0].page_no if element.prov else ""

                image_html = element.export_to_html(doc=picture_res)
                image_data, _ = self._extract_tags(image_html)

                try:
                    page_images[str(element.image.uri)] = {
                        "page_number": (
                            int(page_number) if page_number != "" else page_number
                        ),
                        "caption": image_data[0].get("caption"),
                    }
                except:
                    continue

        with open(
            output_dir / (kebabcase(doc_filename) + "_page_to_text.json"),
            "w",
            encoding="utf-8",
        ) as text_json:
            text_json.write(json.dumps(page_texts, indent=4))

        with open(
            output_dir / (kebabcase(doc_filename) + "_image_to_page.json"),
            "w",
            encoding="utf-8",
        ) as image_json:
            image_json.write(json.dumps(page_images, indent=4))

        with open(
            output_dir / (kebabcase(doc_filename) + "_table_to_page.json"),
            "w",
            encoding="utf-8",
        ) as table_json:
            table_json.write(json.dumps(page_tables, indent=4))

        html_filename = output_dir / f"{kebabcase(doc_filename)}.html"
        conv_res.document.save_as_html(
            html_filename,
            image_mode=ImageRefMode.REFERENCED,
            labels=DEFAULT_EXPORT_LABELS,
        )

        end_time = time.time() - start_time

        _log.info(f"Processed {self.input_path.name} in {end_time:.2f} seconds.")

        # TODO: os erase prev md file if new one created
