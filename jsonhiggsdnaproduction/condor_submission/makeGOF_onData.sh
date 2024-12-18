for year in "run2" #"2016" "2017" "2018" #
do
    for catg in "C" #"2b" "1b"
    do
        datacard=datacards/datacard_bbDM"${year}"_"${catg}"/bbDM_datacard_"${year}"_THDMa_${catg}_allregion_2HDMa_Ma150_MChi1_MA600_tb35_st_0p7.txt
        datacardws=$(echo "$datacard" | sed 's|.txt|.root|g')
        if [ -f "$datacardws" ]; then
            echo "Datacard workspace already exists, continuing..."
        else
            echo "Datacard workspace does not exist, creating it..."
            # Create the datacard workspace
            text2workspace.py "$datacard" --channel-masks
        fi
        echo $datacardws
        for mode in "Test"
        do
            for algorithm in "saturated" #"KS" "AD" #
            do
                combine -M GoodnessOfFit --algo=${algorithm} -m 125 -d $datacardws &
                ##=================================================================
                combine -M GoodnessOfFit --algo=${algorithm} -t 100 --toysFreq -s -1 -m 125 -d $datacardws &
                combine -M GoodnessOfFit --algo=${algorithm} -t 100 --toysFreq -s -1 -m 125 -d $datacardws &
                combine -M GoodnessOfFit --algo=${algorithm} -t 100 --toysFreq -s -1 -m 125 -d $datacardws &
                combine -M GoodnessOfFit --algo=${algorithm} -t 100 --toysFreq -s -1 -m 125 -d $datacardws &
                combine -M GoodnessOfFit --algo=${algorithm} -t 100 --toysFreq -s -1 -m 125 -d $datacardws &
                combine -M GoodnessOfFit --algo=${algorithm} -t 100 --toysFreq -s -1 -m 125 -d $datacardws &
                combine -M GoodnessOfFit --algo=${algorithm} -t 100 --toysFreq -s -1 -m 125 -d $datacardws &
                combine -M GoodnessOfFit --algo=${algorithm} -t 100 --toysFreq -s -1 -m 125 -d $datacardws &
                combine -M GoodnessOfFit --algo=${algorithm} -t 100 --toysFreq -s -1 -m 125 -d $datacardws &
                combine -M GoodnessOfFit --algo=${algorithm} -t 100 --toysFreq -s -1 -m 125 -d $datacardws &
                combine -M GoodnessOfFit --algo=${algorithm} -t 100 --toysFreq -s -1 -m 125 -d $datacardws &
                combine -M GoodnessOfFit --algo=${algorithm} -t 100 --toysFreq -s -1 -m 125 -d $datacardws &
                # # combine -M GoodnessOfFit --algo=${algorithm} -t 100 --toysFreq -s -1 -m 125 -d $datacardws &
                # # combine -M GoodnessOfFit --algo=${algorithm} -t 100 --toysFreq -s -1 -m 125 -d $datacardws &
                # # combine -M GoodnessOfFit --algo=${algorithm} -t 100 --toysFreq -s -1 -m 125 -d $datacardws &
                # # combine -M GoodnessOfFit --algo=${algorithm} -t 100 --toysFreq -s -1 -m 125 -d $datacardws &
                # # combine -M GoodnessOfFit --algo=${algorithm} -t 100 --toysFreq -s -1 -m 125 -d $datacardws &
                # # combine -M GoodnessOfFit --algo=${algorithm} -t 100 --toysFreq -s -1 -m 125 -d $datacardws &
                # # combine -M GoodnessOfFit --algo=${algorithm} -t 100 --toysFreq -s -1 -m 125 -d $datacardws &
                # # combine -M GoodnessOfFit --algo=${algorithm} -t 100 --toysFreq -s -1 -m 125 -d $datacardws &
                ##=================================================================
                wait
                # ${mode}
                hadd higgsCombine${mode}.GoodnessOfFit.mH125.Merged.root higgsCombine${mode}.GoodnessOfFit.mH125.*.root
                ##=================================================================
                ## plotting
                python plotGOF_fromDanyer.py --observed higgsCombine${mode}.GoodnessOfFit.mH125.root --toys higgsCombine${mode}.GoodnessOfFit.mH125.Merged.root  --output gof${mode}_${catg}_${year} --statistic ${algorithm} --bins 100 --title-right="S+B hypothesis("${catg}" "${year}")"
                ##=================================================================
                combineTool.py -M CollectGoodnessOfFit --input higgsCombine${mode}.GoodnessOfFit.mH125.root higgsCombine${mode}.GoodnessOfFit.mH125.Merged.root -m 125.0 -o gof${mode}_${catg}_${year}.json
                plotGof.py gof${mode}_${catg}_${year}.json --statistic ${algorithm} --mass 125.0 -o gof${mode}_${catg}_${year} --title-right="S+B hypothesis("${catg}" "${year}")"
                ##=================================================================
                for f in *gof${mode}_${catg}_${year}*; do mv -v -f -- "$f" ./gofplots_${algorithm} ; done
                ##=================================================================
                rm -rf higgsCombine${mode}*.GoodnessOfFit.*.root
            done
        done
    done
done
