# Re-export submodules so legacy imports like `from bots import rule_based` keep working.
from bots.manual import rule_based, probability
from bots.llms import claude, chatgpt, gemini
