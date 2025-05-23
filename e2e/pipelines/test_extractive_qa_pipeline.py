# SPDX-FileCopyrightText: 2022-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from haystack import Document, Pipeline
from haystack.components.readers import ExtractiveReader
from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
from haystack.document_stores.in_memory import InMemoryDocumentStore


def test_extractive_qa_pipeline(tmp_path):
    # Create the pipeline
    qa_pipeline = Pipeline()
    qa_pipeline.add_component(instance=InMemoryBM25Retriever(document_store=InMemoryDocumentStore()), name="retriever")
    qa_pipeline.add_component(instance=ExtractiveReader(model="deepset/tinyroberta-squad2"), name="reader")
    qa_pipeline.connect("retriever", "reader")

    # Serialize the pipeline to YAML
    with open(tmp_path / "test_bm25_rag_pipeline.yaml", "w") as f:
        qa_pipeline.dump(f)

    # Load the pipeline back
    with open(tmp_path / "test_bm25_rag_pipeline.yaml", "r") as f:
        qa_pipeline = Pipeline.load(f)

    # Populate the document store
    documents = [
        Document(content="My name is Jean and I live in Paris."),
        Document(content="My name is Mark and I live in Berlin."),
        Document(content="My name is Giorgio and I live in Rome."),
    ]
    qa_pipeline.get_component("retriever").document_store.write_documents(documents)

    # Query and assert
    questions = ["Who lives in Paris?", "Who lives in Berlin?", "Who lives in Rome?"]
    answers_spywords = ["Jean", "Mark", "Giorgio"]

    for question, spyword, doc in zip(questions, answers_spywords, documents):
        result = qa_pipeline.run({"retriever": {"query": question}, "reader": {"query": question}})

        extracted_answers = result["reader"]["answers"]

        # we expect at least one real answer and no_answer
        assert len(extracted_answers) > 1

        # the best answer should contain the spyword
        assert spyword in extracted_answers[0].data

        # no_answer
        assert extracted_answers[-1].data is None

        # since these questions are easily answerable, the best answer should have higher score than no_answer
        assert extracted_answers[0].score >= extracted_answers[-1].score

        for answer in extracted_answers:
            assert answer.query == question

            assert hasattr(answer, "score")
            assert hasattr(answer, "document_offset")

            assert hasattr(answer, "document")

        # the top answer is extracted from the correct document
        top_answer = extracted_answers[0]
        if top_answer.document is not None:
            if top_answer.document.id != doc.id:
                print(top_answer.document.id, doc.id)
            assert top_answer.document.id == doc.id
