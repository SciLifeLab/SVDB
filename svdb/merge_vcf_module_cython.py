from __future__ import absolute_import
from . import overlap_module

def retrieve_key(line,key):
    item = False
    if key + "=" in line:
        item=line.strip().split(key+"=")[-1].split(";")[0]
        if(len(item) == len(line.strip())):
            return(False)
    return(item)

def get_CIPOS_CEND(query_variant):
    ciA_query=[0,0]
    CIPOS=retrieve_key(query_variant[-1],"CIPOS")
    if CIPOS:
        CIPOS=CIPOS.split(",")
        if len(CIPOS) == 2:
            ciA_query=[int(CIPOS[0]),int(CIPOS[1])]
        else:
            ciA_query=[int(CIPOS[0]),int(CIPOS[0])]

    ciB_query=[0,0]
    CIPOS=retrieve_key(query_variant[-1],"CIEND")
    if CIPOS:
        CIPOS=CIPOS.split(",")
        if len(CIPOS) == 2:
            ciB_query=[int(CIPOS[0]),int(CIPOS[1])]
        else:
            ciB_query=[int(CIPOS[0]),int(CIPOS[0])]

    return(ciA_query,ciB_query)

def find_ci(query_variant,db_variant):

    ciA_query,ciB_query=get_CIPOS_CEND(query_variant)
    ciA_db,ciB_db=get_CIPOS_CEND(db_variant)

    return(ciA_query,ciB_query,ciA_db,ciB_db)

#merge the csg fields of bnd variants
def merge_csq(info,csq):
    var_csq=info.split("CSQ=")[-1].split(";")[0]
    csq.append(var_csq);
    effects=set([])
    for csq_field in csq:
        effects= effects | set(csq_field.split(","))
    CSQ="CSQ="+",".join(list(effects))
    pre_CSQ=info.split("CSQ=")[0]
    post_CSQ=info.split("CSQ=")[-1].split(";")
    if len(post_CSQ) == 1:
        post_CSQ=""
    else:
        post_CSQ=";"+";".join(post_CSQ[1:])

    info=pre_CSQ+CSQ+post_CSQ

    return(info)

def sort_format_field(line,samples,sample_order,priority_order,files,representing_file,args):
    tmp_format=[]
    var_samples=[]
    i=0
    #sort the format fields
    if not args.same_order:
        for sample in sorted(samples):
            try:
                sample_position=sample_order[sample][representing_file]
                tmp_format.append( line[9+sample_position] )
            except:
                print("ERROR: The input file {} lacks sample {}, use the --same_order setting to disregard the sample ids").format(representing_file,sample)
                quit()
        for format_column in tmp_format:
            line[9+i] = format_column
            i+=1

    #generate a union of the info fields
    info_union=[]
    tags_in_info=[]
    #print "TEST"
    #print priority_order
    for input_file in priority_order:

        if not input_file in files:
            continue
        INFO=files[input_file].strip().split("\t")[7]
        INFO_content=INFO.split(";")
        
        for content in INFO_content:
            tag=content.split("=")[0]
            if not tag in tags_in_info:
                tags_in_info.append(tag)
                info_union.append(content)

    new_info=";".join(info_union)     
    line[7] = new_info
    
    
    return(line)

def merge(variants,samples,sample_order,priority_order,args):
    ci=args.ci
    overlap_param=args.overlap
    bnd_distance=args.bnd_distance
    no_intra=args.no_intra
    no_var=args.no_var
    pass_only=args.pass_only

    #search for similar variants
    to_be_printed={}
    for chrA in variants:

        analysed_variants=set([])
        for i in range(0,len(variants[chrA])):
            if i in analysed_variants:
                continue
            
            merge=[]
            csq=[]

            files={}
            for j in range(i+1,len(variants[chrA])):
                if j in analysed_variants:
                    continue
                #print "i:{}".format(i)
                #print "j:{}".format(j)
                #if the pass_only option is chosen, only variants marked PASS will be merged
                if pass_only:
                    filter_tag=variants[chrA][i][-1].split("\t")[6]
                    if not filter_tag == "PASS" and not filter_tag == ".":
                        break

                            
                #only treat varints on the same pair of chromosomes    
                if not variants[chrA][i][0] == variants[chrA][j][0]:
                    continue

                #if the pass_only option is chosen, only variants marked PASS will be merged
                if pass_only:
                    filter_tag=variants[chrA][j][-1].split("\t")[6]
                    if not filter_tag == "PASS" and not filter_tag == ".":
                        continue

                #dont merge variants of different type
                if not variants[chrA][i][1] == variants[chrA][j][1] and not no_var:
                    continue

                #if no_intra is chosen, variants may only be merged if they belong to different input files
                if no_intra and variants[chrA][i][-3] == variants[chrA][j][-3]:
                    continue

                overlap = False
                if not ci:
                    overlap=overlap_module.variant_overlap(chrA,variants[chrA][i][0],variants[chrA][i][2],variants[chrA][i][3],variants[chrA][j][2],variants[chrA][j][3],overlap_param,bnd_distance)
                else:
                    ciA_query,ciB_query,ciA_db,ciB_db=find_ci(variants[chrA][i],variants[chrA][j])
                    overlap=overlap_module.ci_overlap(variants[chrA][i][2],variants[chrA][i][3],ciA_query,ciB_query,variants[chrA][j][2],variants[chrA][j][3],ciA_db,ciB_db)

                if overlap:
                    #add similar variants to the merge list and remove them
                    if args.priority:
                        files[variants[chrA][j][-3]] = variants[chrA][j][-1]
                        merge.append(variants[chrA][j][-1].split("\t")[2].replace(";","_")+":"+variants[chrA][j][-3])
                    else:
                        files[ variants[chrA][j][-3].replace(".vcf","").split("/")[-1] ] = variants[chrA][j][-1]
                        merge.append(variants[chrA][j][-1].split("\t")[2].replace(";","_")+":"+variants[chrA][j][-3].replace(".vcf","").split("/")[-1])

                    if variants[chrA][i][0] != chrA and "CSQ=" in variants[chrA][j][-1]:
                        info=variants[chrA][j][-1].split("\t")[7]
                        csq.append(info.split("CSQ=")[-1].split(";")[0])
                    analysed_variants.add(j)
            
            line=variants[chrA][i][-1].split("\t")
            if merge:
                line[7] += ";VARID=" + "|".join(merge)

            if csq:
                line[7]=merge_csq(line[7],csq)
            if not line[0] in to_be_printed:
                to_be_printed[line[0]]=[]
            if args.same_order:
                to_be_printed[line[0]].append(line)
            else:
                
                if args.priority:
                    files[variants[chrA][i][-3]] = "\t".join(line)
                    representing_file = variants[chrA][i][-3]
                else:
                    files[ variants[chrA][i][-3].replace(".vcf","").split("/")[-1] ] = "\t".join(line)
                    representing_file = variants[chrA][i][-3].replace(".vcf","").split("/")[-1]
                
                line=sort_format_field(line,samples,sample_order,priority_order,files, representing_file,args)
                
                to_be_printed[line[0]].append(line)
            
            analysed_variants.add(i)


    return(to_be_printed)
