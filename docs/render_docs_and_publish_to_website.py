
import hazelbean as hb 
import os

cwd = os.path.abspath(os.getcwd())
print('Current working directory:', cwd)

book_name = 'hazelbean'


# STATUS UPDATE 2023-09-01: Almost working, but had to switch away due to time. Next steps would be to finish 
# working the Testing Suite into the docs so that they serve as examples.

## Note that unlike in other projects, because of the unique repo name requirement of hosting on github.io, this doesnt use the bookname
# print('Changed working directory to:', book_name)

render_book = 1
if render_book:   
    always_render = True
    render_prefix = '../RENDERED_'
    render_dir = render_prefix + book_name
    if not hb.path_exists(render_dir, verbose=True) or always_render:
        hb.create_directories(render_dir)
        os.system("quarto render .")

copy_to_website_repo = 0
if copy_to_website_repo:
    src_dir = 'RENDERED_website'
    dst_dir = '../../Website/jandrewjohnson.github.io'

    print('Copying from: ', os.path.abspath(src_dir))
    print('Copying to: ', os.path.abspath(dst_dir))

    hb.copy_file_tree_to_new_root(src_dir, dst_dir)

    also_push_to_website_repo = 1
    if also_push_to_website_repo:
        print('Pushing to website repo')
        os.chdir(dst_dir)
        os.system('git pull')
        os.system('git status')
        print(os.system('git status'))
        os.system('git remote -v')
        a = os.listdir(os.getcwd())
        print(a)
        os.system('git add .')
        os.system('git commit -m "Update website"')
        os.system('git push')
        os.system('git status')