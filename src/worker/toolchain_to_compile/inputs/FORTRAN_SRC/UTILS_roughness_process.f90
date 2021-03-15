!######################################################################
!# ©Zephy-Science 2013                                                #
!# GPL3 Licence                                                       #
!######################################################################
!# Roughness Data Evaluation for ground meshes                        #
!######################################################################

PROGRAM     UTILS_roughness_process
IMPLICIT    NONE

integer:: ifacfile,imapfile,ioutfile,nval,ifac,imap,ichar1,ichar2,nfac
integer:: ncharfacfile,ncharmapfile,ncharoutfile,ncharlogfile,arg_size,arg_status
integer,dimension(:,:),pointer:: fac_int
real:: avancement,xp,yp,rough,dx,dy,dist,dmin,rnval
real,dimension(:),pointer:: m1,m2,m3
real,dimension(:,:),pointer:: fac_real
character(len=3):: format
character(len=5):: frac
character(len=500):: facfile,mapfile,outfile,logfile,arg_content
character(len=1000):: line,newline

CALL get_command_argument(1,arg_content,arg_size,arg_status)
ncharfacfile=arg_size
facfile(1:ncharfacfile)=arg_content(1:arg_size)
CALL get_command_argument(2,arg_content,arg_size,arg_status)
ncharmapfile=arg_size
mapfile(1:ncharmapfile)=arg_content(1:arg_size)
CALL get_command_argument(3,arg_content,arg_size,arg_status)
ncharoutfile=arg_size
outfile(1:ncharoutfile)=arg_content(1:arg_size)
CALL get_command_argument(4,arg_content,arg_size,arg_status)
ncharlogfile=arg_size
logfile(1:ncharlogfile)=arg_content(1:arg_size)

ifacfile=1
imapfile=2
ioutfile=3

nfac=0

open(ifacfile,file=facfile(1:ncharfacfile),status='old',action='read')
do
    read(ifacfile,*,end=662)
    nfac=nfac+1
enddo
662 ALLOCATE(fac_int(nfac,4))
ALLOCATE(fac_real(nfac,2))
rewind(ifacfile)

do ifac=1,nfac
    read(ifacfile,*) fac_int(ifac,1),fac_int(ifac,2),fac_int(ifac,3),fac_int(ifac,4)&
    &,fac_real(ifac,1),fac_real(ifac,2)
enddo
close(ifacfile)

if (mapfile(ncharmapfile-1:ncharmapfile).ne.'_a')then

    open(imapfile,file=mapfile(1:ncharmapfile)//'.info',form='formatted',status='old',action='read')
    read(imapfile,*) format
    read(imapfile,*) nval
    close(imapfile)

    allocate(m1(nval)) ; allocate(m2(nval)) ; allocate(m3(nval))

    open(imapfile,file=mapfile(1:ncharmapfile),form='unformatted',status='old',action='read')
    read(imapfile) m1 ; read(imapfile) m2 ; read(imapfile) m3
    close(imapfile)

else

    open(imapfile,file=mapfile(1:ncharmapfile),status='old',action='read')
    read(imapfile,*) format ; read(imapfile,*) rnval ; nval=int(rnval)
    allocate(m1(nval)) ; allocate(m2(nval)) ; allocate(m3(nval))
    do imap=1,nval
        read(imapfile,*) m1(imap),m2(imap),m3(imap)
    enddo
    close(imapfile)

endif

open(ioutfile,file=outfile(1:ncharoutfile),status='replace',action='write')

do ifac=1,nfac

    if(logfile(1:ncharlogfile).ne.'NONE')then

        if(modulo(ifac,50).eq.0)then
            avancement=float(ifac)/nfac
            open(1,file=logfile(1:ncharlogfile),status='old',action='read',err=900)
            read(1,'(a)',end=900,err=900) line
            close(1)
            ichar1= index(line,'<progress_frac>')+15
            ichar2= index(line,'</progress_frac>')
            write(frac,'(f5.3)') avancement
            newline=line(1:ichar1)//frac//line(ichar2:)
            open(2,file=logfile(1:ncharlogfile),status='old',action='write',err=900)
            write(2,'(a)') newline
            close(2)
900         continue
        endif

    endif

    xp=fac_real(ifac,1)
    yp=fac_real(ifac,2)
    dmin =+1.e20
    rough=-999.
    do imap=1,nval
        dx=m1(imap)-xp
        dy=m2(imap)-yp
        dist=dx*dx+dy*dy
        if(dist.lt.dmin)then
            dmin=dist
            rough=m3(imap)
        endif
    enddo
    write(ioutfile,*) fac_int(ifac,1),fac_int(ifac,2),fac_int(ifac,3),fac_int(ifac,4) &
    &,fac_real(ifac,1),fac_real(ifac,2),rough

enddo

close(ioutfile)

if(logfile(1:ncharlogfile).ne.'NONE')then
	avancement=1.
	open(1,file=logfile(1:ncharlogfile),status='old',action='read',err=900)
	read(1,'(a)',end=902,err=902) line
	close(1)
	ichar1= index(line,'<progress_frac>')+15
	ichar2= index(line,'</progress_frac>')
	write(frac,'(f5.3)') avancement
	newline=line(1:ichar1)//frac//line(ichar2:)
	open(2,file=logfile(1:ncharlogfile),status='old',action='write',err=900)
	write(2,'(a)') newline
	close(2)
902 continue
endif

END PROGRAM UTILS_roughness_process
