import os 


def check_save_location(path):
  if os.path.isdir(path):
    # if path exists, check if directory already has files other than gitignore and get user confirmation before possible overwrites
    if os.listdir(path) != [".gitignore"] and os.listdir(path):
      print(f"Target save location {path} contains existing files, which may be overwritten. Files:")
      print("\t", "\n\t ".join(os.listdir(path)))
      user_input = input("Continue? (y/n): ")
      while user_input not in ["y","n"]:
        user_input = input("(y/n): ")
      if user_input == "y":
        return True
    return False

  else:
    # if path does not exist, create one if user wants 
    user_input = input(f"Target save location {path} does not exist! Create folder? (y/n): ")
    while user_input not in ["y","n"]:
      user_input = input("(y/n): ")
    if user_input == "y":
      os.makedirs(path)
      return True
    return False