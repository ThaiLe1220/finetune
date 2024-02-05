import evaluate
import os
from transformers import AutoTokenizer
from datasets import load_dataset
import numpy as np
from IPython.display import display, HTML
from transformers import AutoTokenizer
from transformers import (
    AutoModelForSeq2SeqLM,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
    MarianMTModel,
    MarianTokenizer,
    EarlyStoppingCallback,
)


# Disable WANDB (Weights & Biases) for this session
os.environ["WANDB_DISABLED"] = "true"

# Set source and target languages for translation
SOURCE_LANG = "de"
TARGET_LANG = "en"

# Load dataset and metric for evaluation (BLEU score)
raw_datasets = load_dataset("Eugenememe/netflix-de-en")
metric = evaluate.load("sacrebleu")

# Define tokenizer and model checkpoint from Hugging Face
MODEL_CHECKPOINT = "Helsinki-NLP/opus-mt-de-en"
tokenizer = AutoTokenizer.from_pretrained(MODEL_CHECKPOINT)

# Set prefix, maximum input and output lengths for tokenization
PREFIX = ""
MAX_INPUT_LENGTH = 128
MAX_TARGET_LENGTH = 128


# Preprocessing function to tokenize the dataset
def preprocess_function(examples):
    inputs = [PREFIX + ex[SOURCE_LANG] for ex in examples["translation"]]
    targets = [ex[TARGET_LANG] for ex in examples["translation"]]
    model_inputs = tokenizer(inputs, max_length=MAX_INPUT_LENGTH, truncation=True)

    # Tokenize the targets
    with tokenizer.as_target_tokenizer():
        labels = tokenizer(targets, max_length=MAX_TARGET_LENGTH, truncation=True)
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs


# Apply the preprocessing function to the dataset
tokenized_datasets = raw_datasets.map(preprocess_function, batched=True)

# Load the model for seq2seq language modeling
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_CHECKPOINT)

# Load the model from a checkpoint
# CHECKPOINT_PATH = "opus-mt-en-es-finetuned/checkpoint-3582"
# model = AutoModelForSeq2SeqLM.from_pretrained(CHECKPOINT_PATH)

# Define batch size and model name derived from checkpoint
BATCH_SIZE = 64
MODEL_NAME = MODEL_CHECKPOINT.rsplit("/", maxsplit=1)[-1]

# Set training arguments for the model
args = Seq2SeqTrainingArguments(
    output_dir=f"{MODEL_NAME}-finetuned",
    evaluation_strategy="epoch",
    save_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE,
    weight_decay=0.01,
    save_total_limit=1,
    num_train_epochs=5,
    predict_with_generate=True,
    logging_dir="./logs",
    logging_steps=100,
    load_best_model_at_end=True,
    metric_for_best_model="loss",
    greater_is_better=False,
)

# Create a data collator for handling batch data
data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)


# Function for postprocessing the text
def postprocess_text(preds, labels):
    preds = [pred.strip() for pred in preds]
    labels = [[label.strip()] for label in labels]
    return preds, labels


# Function to compute metrics for evaluation
def compute_metrics(eval_preds):
    preds, labels = eval_preds
    if isinstance(preds, tuple):
        preds = preds[0]
    decoded_preds = tokenizer.batch_decode(preds, skip_special_tokens=True)
    labels = np.where(labels != -100, labels, tokenizer.pad_token_id)
    decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)
    decoded_preds, decoded_labels = postprocess_text(decoded_preds, decoded_labels)
    result = metric.compute(predictions=decoded_preds, references=decoded_labels)
    result = {"bleu": result["score"]}
    prediction_lens = [
        np.count_nonzero(pred != tokenizer.pad_token_id) for pred in preds
    ]
    result["gen_len"] = np.mean(prediction_lens)
    return {k: round(v, 4) for k, v in result.items()}


# Initialize and run the trainer
trainer = Seq2SeqTrainer(
    model,
    args,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["validation"],
    data_collator=data_collator,
    tokenizer=tokenizer,
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
)

trainer.train()
trainer.save_model(f"{MODEL_NAME}-finetuned")

# Print out saved model files
for dirname, _, filenames in os.walk(f"{MODEL_NAME}-finetuned"):
    for filename in filenames:
        print(os.path.join(dirname, filename))

# Translate a sample text to test the model
src_text = [
    "My name is Sarah, I live in London with my family and I absolutely love every bit of it."
]
FINETUNED_MODEL_NAME = f"{MODEL_NAME}-finetuned"
tokenizer = MarianTokenizer.from_pretrained(FINETUNED_MODEL_NAME)
finetuned_model = MarianMTModel.from_pretrained(FINETUNED_MODEL_NAME)
translated = finetuned_model.generate(
    **tokenizer(src_text, return_tensors="pt", padding=True)
)
print([tokenizer.decode(t, skip_special_tokens=True) for t in translated])
